"""
Exploratory query: all events where appId == "OneHome", last 90 days.

Run from the repo root:
    python projects/20260423_mixpanel-oh-flows/explore_onehome_events.py

Outputs:
    projects/20260423_mixpanel-oh-flows/data/raw/onehome_events_raw.json
    projects/20260423_mixpanel-oh-flows/data/processed/onehome_events.csv
"""
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.common.export import write_csv, write_json
from src.connectors.mixpanel import MixpanelClient

APP_ID = "OneHome"
N_DAYS = 90

_PROJECT_DIR = Path(__file__).parent
OUTPUT_RAW = _PROJECT_DIR / "data" / "raw"
OUTPUT_PROCESSED = _PROJECT_DIR / "data" / "processed"


def main() -> None:
    client = MixpanelClient()

    print(f"Querying Mixpanel: events where appId='{APP_ID}', last {N_DAYS} days...")
    rows = client.event_counts_by_app(app_id=APP_ID, n_days=N_DAYS)

    if not rows:
        print("No events returned. Check credentials, project ID, and whether appId property exists.")
        return

    write_json(OUTPUT_RAW / "onehome_events_raw.json", rows)
    write_csv(OUTPUT_PROCESSED / "onehome_events.csv", rows)

    total_events = sum(r.get("count", 0) for r in rows)

    print(f"\n{'Event':<55} {'Count':>10}")
    print("-" * 67)
    for r in rows:
        print(f"{r['event']:<55} {r['count']:>10,}")
    print("-" * 67)
    print(f"{'TOTAL':<55} {total_events:>10,}")
    print(f"\n{len(rows)} distinct events  |  {total_events:,} total occurrences")
    print(f"\nSaved:")
    print(f"  {OUTPUT_RAW / 'onehome_events_raw.json'}")
    print(f"  {OUTPUT_PROCESSED / 'onehome_events.csv'}")


if __name__ == "__main__":
    main()
