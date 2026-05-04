"""
Directly probe candidate user/agent properties on OneHome events.
Rather than inspecting structure, we query known candidate property names
and see which ones have real values.

Run:
    python projects/20260423_mixpanel-oh-flows/inspect_event_properties.py
"""
import sys
import time
from pathlib import Path
from datetime import date, timedelta

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.common.export import write_json
from src.connectors.mixpanel import MixpanelClient

APP_ID = "OneHome"
DAYS = 7
START = (date.today() - timedelta(days=DAYS)).isoformat()
END = date.today().isoformat()

# Candidate properties — grouped by what we're trying to learn
# Run 1 results (2026-05-03):
#   AgentID       → 113M events, 291k distinct values  ✅ USE THIS
#   agentId       → 55k events, 19k distinct            (manual on specific events only)
#   AgentId       → 2k events, 587 distinct             (old/rare variant)
#   authenticated → 113M events, 2 values: false(76.7M) / true(36.5M)  ✅ USE THIS
#   All others in run 1 (userType, role, memberType, isAgent, userId, etc.) → EMPTY
#
# Run 2 — only probe what was rate-limited:
CANDIDATE_PROPS = [
    # Entry / referral context
    "ViewMode", "viewMode",

    # Platform / device (from source: setupDeviceData registers these)
    "isMobileApp", "deviceType", "model", "os",

    # MLS / brokerage context
    "MLSID", "AssociationID",

    # Confirm appId works (sanity check)
    "appId",
]

_PROJECT_DIR = Path(__file__).parent
OUTPUT_RAW = _PROJECT_DIR / "data" / "raw"
OUTPUT_PROCESSED = _PROJECT_DIR / "data" / "processed"


def probe_property(client: MixpanelClient, prop: str) -> dict:
    """Return top values for a property using the Events Properties Values endpoint.
    This uses a separate rate limit bucket from JQL (400 queries/hour)."""
    url = "https://mixpanel.com/api/query/events/properties/values"
    params = {
        "project_id": client.project_id,
        "name": prop,
        "from_date": START,
        "to_date": END,
        "limit": 20,
    }
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        resp = __import__("requests").get(
            url,
            headers=client._headers(),
            params=params,
            timeout=30,
            verify=client.verify,
        )
    if resp.status_code == 400:
        # Property doesn't exist or no data
        return {"total_non_null": 0, "distinct_values": 0, "top_values": []}
    if not resp.ok:
        body = resp.text.strip()
        raise RuntimeError(f"HTTP {resp.status_code}: {body[:300]}")
    data = resp.json()
    values = data if isinstance(data, list) else data.get("results", [])
    return {"total_non_null": None, "distinct_values": len(values), "top_values": [{"value": v} for v in values]}


def main() -> None:
    client = MixpanelClient()
    results = {}

    print(f"Probing {len(CANDIDATE_PROPS)} candidate properties on OneHome events ({DAYS}-day window)...\n")
    print(f"{'Property':<30} {'Non-null events':>15}  {'Distinct vals':>13}  Top values")
    print("-" * 100)

    for prop in CANDIDATE_PROPS:
        time.sleep(65)  # stay under 60 queries/hour rate limit
        try:
            info = probe_property(client, prop)
            total = info["total_non_null"]
            distinct = info["distinct_values"]
            top = [f"{r['value']} ({r['count']:,})" for r in info["top_values"][:3]]
            results[prop] = info
            if total > 0:
                print(f"  {prop:<28} {total:>15,}  {distinct:>13,}  {', '.join(top)}")
            else:
                print(f"  {prop:<28} {'(empty)':>15}")
        except Exception as e:
            print(f"  {prop:<28} ERROR: {e}")
            results[prop] = {"error": str(e)}

    write_json(OUTPUT_RAW / "onehome_property_probe.json", results)
    print(f"\nSaved: {OUTPUT_RAW / 'onehome_property_probe.json'}")

    # --- PropertyFit recency check ---
    print("\n--- PropertyFit recency check (last 7 days vs last 90 days) ---")
    pf_event = "PropertyFit Onboarding - Flow - What describes you best? - Choice Selection"
    for window, label in [(7, "last 7d"), (90, "last 90d")]:
        w_start = (date.today() - timedelta(days=window)).isoformat()
        jql = f"""
        function main() {{
          return Events({{from_date: '{w_start}', to_date: '{END}'}})
            .filter(function(e) {{
              return e.properties && e.properties.appId === '{APP_ID}'
                && e.name === '{pf_event}';
            }})
            .reduce(mixpanel.reducer.count());
        }}
        """.strip()
        try:
            r = client.run_jql(jql)
            count = r.get("results", [0])[0] if isinstance(r.get("results"), list) else 0
            print(f"  {label}: {count:,} events")
        except Exception as e:
            print(f"  {label}: ERROR {e}")


if __name__ == "__main__":
    main()
