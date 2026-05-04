import base64
import json
import os
import random
import time
from datetime import date, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


class MixpanelClient:
    def __init__(self) -> None:
        load_dotenv()
        self.project_id = os.getenv("MIXPANEL_PROJECT_ID", "").strip()
        self.username = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USERNAME", "").strip()
        self.secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET", "").strip()
        self.base_url = os.getenv("MIXPANEL_API_BASE", "https://mixpanel.com/api/query").strip()
        verify_ssl_value = os.getenv("MIXPANEL_VERIFY_SSL", "true").strip().lower()
        self.ca_bundle = os.getenv("MIXPANEL_CA_BUNDLE", "").strip()
        # Mixpanel Query API limit includes 60 queries/hour; default to one request per 61 seconds.
        self.min_request_interval_seconds = float(
            os.getenv("MIXPANEL_MIN_REQUEST_INTERVAL_SECONDS", "61").strip() or "61"
        )
        self.max_retries = int(os.getenv("MIXPANEL_MAX_RETRIES", "6").strip() or "6")
        self._next_request_ts = 0.0
        self._rate_lock = Lock()

        if not self.username or not self.secret:
            raise ValueError(
                "Missing Mixpanel service account credentials. Populate .env from .env.example first."
            )

        if verify_ssl_value in {"0", "false", "no"}:
            self.verify: Any = False
        elif self.ca_bundle:
            self.verify = self.ca_bundle
        else:
            self.verify = True

    def _headers(self) -> Dict[str, str]:
        creds = f"{self.username}:{self.secret}".encode("utf-8")
        auth = base64.b64encode(creds).decode("utf-8")
        return {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        }

    def _wait_for_rate_limit_window(self) -> None:
        if self.min_request_interval_seconds <= 0:
            return

        with self._rate_lock:
            now = time.monotonic()
            wait_seconds = self._next_request_ts - now
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._next_request_ts = time.monotonic() + self.min_request_interval_seconds

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> requests.Response:
        attempts = 0
        while True:
            self._wait_for_rate_limit_window()
            response = requests.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                data=data,
                timeout=timeout,
                verify=self.verify,
            )

            if response.status_code != 429:
                return response

            if attempts >= self.max_retries:
                body = response.text.strip()
                raise RuntimeError(
                    f"Mixpanel request hit repeated rate limits (429) after {attempts + 1} attempts: {body[:300]}"
                )

            retry_after = response.headers.get("Retry-After", "").strip()
            retry_after_seconds = 0.0
            if retry_after:
                try:
                    retry_after_seconds = float(retry_after)
                except ValueError:
                    retry_after_seconds = 0.0

            # Exponential backoff with light jitter for contention relief.
            backoff_seconds = min(2**attempts, 60)
            sleep_seconds = max(retry_after_seconds, backoff_seconds) + random.uniform(0, 0.5)
            time.sleep(sleep_seconds)
            attempts += 1

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = self._request("GET", url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()

    def run_jql(self, script: str) -> Dict[str, Any]:
        # JQL endpoint is under /api/query/jql and accepts script in form data.
        url = "https://mixpanel.com/api/query/jql"
        payload: Dict[str, Any] = {"script": script}
        if self.project_id:
            payload["project_id"] = self.project_id

        response = self._request("POST", url, data=payload, timeout=90)
        if not response.ok:
            body = response.text.strip()
            raise RuntimeError(
                f"Mixpanel JQL request failed ({response.status_code}): {body[:600]}"
            )

        text = response.text.strip()
        if not text:
            return {"results": []}

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return {"results": data}
            if isinstance(data, dict):
                return data
            return {"results": [data]}
        except json.JSONDecodeError:
            return {"results": [text]}

    def event_counts_last_n_days(self, n_days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        # WARNING: This method has NO appId filter. It returns events across ALL apps in the
        # Mixpanel project (Matrix, OneHome, Realist, Agent Portal, etc.).
        # DO NOT use this for OneHome analysis — use event_counts_by_app(app_id='OneHome') instead.
        start = date.today() - timedelta(days=n_days)
        end = date.today()

        jql = f"""
        function main() {{
          return Events({{
            from_date: '{start.isoformat()}',
            to_date: '{end.isoformat()}'
          }})
          .groupBy(['name'], mixpanel.reducer.count())
          .map(function(r) {{
            return {{event: r.key[0], count: r.value}};
          }})
                    .sortDesc('count');
        }}
        """.strip()

        result = self.run_jql(jql)
        rows = result.get("results", [])
        return rows[:limit]

    def _get_v2(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET against the /api/2.0/ REST endpoints (separate from the /api/query/ JQL base)."""
        url = f"https://mixpanel.com/api/2.0{path}"
        response = self._request("GET", url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()

    def event_properties(self, event_name: str, days: int = 7) -> List[str]:
        """Return all property names tracked on a given event."""
        from datetime import date, timedelta
        params: Dict[str, Any] = {
            "event": event_name,
            "type": "general",
            "unit": "day",
            "interval": days,
        }
        if self.project_id:
            params["project_id"] = self.project_id
        data = self._get_v2("/events/properties", params=params)
        return list(data.get("data", {}).keys())

    def property_values(
        self,
        event_name: str,
        prop_name: str,
        days: int = 7,
        limit: int = 20,
    ) -> List[Any]:
        """Return top distinct values for a property on a given event."""
        params: Dict[str, Any] = {
            "event": event_name,
            "name": prop_name,
            "type": "general",
            "unit": "day",
            "interval": days,
            "limit": limit,
        }
        if self.project_id:
            params["project_id"] = self.project_id
        data = self._get_v2("/events/properties/values", params=params)
        return data.get("data", [])

    def event_property_keys_jql(self, event_name: str, app_id: str, days: int = 3) -> Dict[str, int]:
        """Use JQL groupBy with custom reducer to collect property keys + occurrence count."""
        from datetime import date, timedelta
        start = (date.today() - timedelta(days=days)).isoformat()
        end = date.today().isoformat()
        jql = f"""
        function main() {{
          return Events({{
            from_date: '{start}',
            to_date:   '{end}'
          }})
          .filter(function(e) {{
            return e.name === {repr(event_name)}
              && e.properties
              && e.properties.appId === '{app_id}';
          }})
          .groupBy(['name'], function(accum, events) {{
            var keys = accum || {{}};
            events.forEach(function(e) {{
              Object.keys(e.properties || {{}}).forEach(function(k) {{
                keys[k] = (keys[k] || 0) + 1;
              }});
            }});
            return keys;
          }});
        }}
        """.strip()
        result = self.run_jql(jql)
        rows = result.get("results", [])
        # groupBy returns [{key: [event_name], value: {prop: count, ...}}]
        if rows and isinstance(rows[0], dict) and "value" in rows[0]:
            return rows[0]["value"]
        return {}

    def event_counts_by_app(
        self,
        app_id: str,
        n_days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Return all event names (and their total count) where properties.appId == app_id,
        sorted descending by count, over the last n_days.

        Note: 'Basic Event Cleaner' is a UI-side Data View / computed property in Mixpanel
        and cannot be applied in JQL. Apply it manually in the UI when cross-checking numbers.
        """
        start = (date.today() - timedelta(days=n_days)).isoformat()
        end = date.today().isoformat()

        jql = f"""
        function main() {{
          return Events({{
            from_date: '{start}',
            to_date:   '{end}'
          }})
          .filter(function(e) {{
            return e.properties && e.properties.appId === '{app_id}';
          }})
          .groupBy(['name'], mixpanel.reducer.count())
          .map(function(r) {{
            return {{ event: r.key[0], count: r.value }};
          }})
          .sortDesc('count');
        }}
        """.strip()

        result = self.run_jql(jql)
        return result.get("results", [])

    def simple_funnel_last_7_days(
        self,
        step1_event: str,
        step2_event: str,
    ) -> Dict[str, Any]:
        start = (date.today() - timedelta(days=7)).isoformat()
        end = date.today().isoformat()

        jql = f"""
        function main() {{
          var usersStep1 = Events({{from_date: '{start}', to_date: '{end}'}})
            .filter(function(e) {{ return e.name === '{step1_event}'; }})
            .groupByUser(mixpanel.reducer.any());

          var usersStep2 = Events({{from_date: '{start}', to_date: '{end}'}})
            .filter(function(e) {{ return e.name === '{step2_event}'; }})
            .groupByUser(mixpanel.reducer.any());

          var s1 = usersStep1.count();
          var s2 = usersStep2.join(usersStep1, function(left, right) {{ return left; }}).count();

          return [{{
            step1_event: '{step1_event}',
            step2_event: '{step2_event}',
            step1_users: s1,
            step2_users: s2,
            conversion_rate: s1 > 0 ? (s2 / s1) : 0
          }}];
        }}
        """.strip()

        result = self.run_jql(jql)
        rows = result.get("results", [])
        return rows[0] if rows else {}
