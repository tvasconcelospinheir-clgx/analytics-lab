import base64
import json
import os
from datetime import date, timedelta
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

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=60,
            verify=self.verify,
        )
        response.raise_for_status()
        return response.json()

    def run_jql(self, script: str) -> Dict[str, Any]:
        # JQL endpoint is under /api/query/jql and accepts script in form data.
        url = "https://mixpanel.com/api/query/jql"
        payload: Dict[str, Any] = {"script": script}
        if self.project_id:
            payload["project_id"] = self.project_id

        response = requests.post(
            url,
            headers=self._headers(),
            data=payload,
            timeout=90,
            verify=self.verify,
        )
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
        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=60,
            verify=self.verify,
        )
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
        sorted descending by count, over the last n_days."""
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
