import subprocess
from pathlib import Path
from typing import List, Optional


class GitHubCliClient:
    """Small wrapper around gh CLI for org-level code search."""

    def __init__(self, gh_path: Optional[str] = None) -> None:
        if gh_path:
            self.gh = Path(gh_path)
        else:
            # Fallback to the portable binary path used in this environment.
            self.gh = Path.home() / "AppData" / "Local" / "Temp" / "ghcli" / "bin" / "gh.exe"

        if not self.gh.exists():
            raise FileNotFoundError(
                f"gh executable not found at {self.gh}. Install GitHub CLI or pass gh_path."
            )

    def _run(self, args: List[str]) -> str:
        result = subprocess.run(
            [str(self.gh), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    def auth_status(self) -> str:
        return self._run(["auth", "status"])

    def search_code(self, query: str, limit: int = 30) -> str:
        return self._run(["search", "code", query, "--limit", str(limit)])
