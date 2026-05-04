import base64
import os
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


class ConfluenceClient:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.getenv("CONFLUENCE_BASE_URL", "").rstrip("/").strip()
        self.email = os.getenv("CONFLUENCE_EMAIL", "").strip()
        self.api_token = os.getenv("CONFLUENCE_API_TOKEN", "").strip()
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "").strip()
        self.page_limit = int(os.getenv("CONFLUENCE_PAGE_LIMIT", "25"))
        verify_ssl_value = os.getenv("CONFLUENCE_VERIFY_SSL", "true").strip().lower()
        self.ca_bundle = os.getenv("CONFLUENCE_CA_BUNDLE", "").strip()

        if not self.base_url or not self.email or not self.api_token or not self.space_key:
            raise ValueError(
                "Missing Confluence credentials/config. Populate CONFLUENCE_* variables in .env."
            )

        if verify_ssl_value in {"0", "false", "no"}:
            self.verify: Any = False
        elif self.ca_bundle:
            self.verify = self.ca_bundle
        else:
            self.verify = True

    def _headers(self) -> Dict[str, str]:
        creds = f"{self.email}:{self.api_token}".encode("utf-8")
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

    def fetch_pages(self) -> List[Dict[str, Any]]:
        cql = f"space={self.space_key} and type=page order by lastmodified desc"
        params: Dict[str, Any] = {
            "cql": cql,
            "limit": self.page_limit,
            "expand": "space,version,body.storage",
        }

        payload = self._get("/wiki/rest/api/content/search", params=params)
        results = payload.get("results", [])
        pages: List[Dict[str, Any]] = []
        for row in results:
            pages.append(
                {
                    "id": row.get("id", ""),
                    "title": row.get("title", "Untitled"),
                    "space": (row.get("space") or {}).get("key", self.space_key),
                    "version": ((row.get("version") or {}).get("number") or ""),
                    "updated_at": ((row.get("version") or {}).get("when") or ""),
                    "html": (((row.get("body") or {}).get("storage") or {}).get("value") or ""),
                }
            )

        return pages


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def html_to_text(html: str) -> str:
    without_tags = _TAG_RE.sub(" ", html)
    text = unescape(without_tags)
    text = _WS_RE.sub(" ", text).strip()
    return text


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or "untitled"


def write_context_files(pages: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: List[str] = []
    for page in pages:
        page_id = str(page.get("id", ""))
        title = str(page.get("title", "Untitled"))
        fname = f"{safe_filename(title)[:80]}_{page_id}.md"
        path = output_dir / fname

        body_text = html_to_text(str(page.get("html", "")))
        summary = body_text[:4000]

        content = [
            f"# {title}",
            "",
            f"- Confluence Page ID: {page_id}",
            f"- Space: {page.get('space', '')}",
            f"- Version: {page.get('version', '')}",
            f"- Updated: {page.get('updated_at', '')}",
            "",
            "## Extracted Text",
            "",
            summary if summary else "(No content extracted)",
            "",
        ]
        path.write_text("\n".join(content), encoding="utf-8")
        written_files.append(fname)

    index_path = output_dir / "README.md"
    generated_at = datetime.now(timezone.utc).isoformat()
    index_lines = [
        "# Confluence Context Cache",
        "",
        "Local snapshots pulled from Confluence to provide documentation context in workspace chats.",
        "",
        f"Generated at (UTC): {generated_at}",
        f"Pages cached: {len(written_files)}",
        "",
        "## Files",
        "",
    ]
    for name in written_files:
        index_lines.append(f"- {name}")

    index_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Re-run the Confluence sync task to refresh this cache.",
            "- These files are plain-text extracts for chat context, not full-fidelity Confluence renders.",
        ]
    )
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    return {
        "generated_at": generated_at,
        "page_count": len(written_files),
        "output_dir": str(output_dir),
        "files": written_files,
    }
