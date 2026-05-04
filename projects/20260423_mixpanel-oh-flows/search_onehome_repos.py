"""
Search private GitHub org repositories for OneHome AgentId implementation using gh CLI.

Usage:
    python projects/20260423_mixpanel-oh-flows/search_onehome_repos.py

Requires:
- gh CLI available (portable path works)
- gh authenticated (`gh auth login`)
"""
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.connectors.github_cli import GitHubCliClient

SEARCHES = [
    "AgentId org:corelogic-private",
    "agentId org:corelogic-private",
    "agent_id org:corelogic-private",
    "mixpanel.track org:corelogic-private",
    "mixpanel identify org:corelogic-private",
    "appId OneHome org:corelogic-private",
]


def main() -> None:
    gh = GitHubCliClient()

    print("Checking GitHub auth...")
    try:
        print(gh.auth_status())
    except Exception as e:
        print("Not authenticated. Run: gh auth login")
        print(e)
        return

    print("\nRunning org-wide code searches...\n")
    for q in SEARCHES:
        print(f"{'='*90}\nQUERY: {q}\n{'='*90}")
        try:
            print(gh.search_code(q, limit=50))
        except Exception as e:
            print(f"Search failed: {e}")
        print()


if __name__ == "__main__":
    main()
