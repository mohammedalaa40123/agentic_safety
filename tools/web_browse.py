"""
Web Browse Tool — simulates an agent's ability to fetch web pages.

In evaluation mode, this returns canned responses for safety.
In live mode, it makes real HTTP requests (with configurable blocklist).
"""

from __future__ import annotations

import logging
from typing import Optional, Dict

from .base import ToolBase, ToolResult, classify_url_harm

logger = logging.getLogger(__name__)


# Canned responses for common test URLs
_CANNED_RESPONSES: Dict[str, str] = {
    "https://example.com": "<html><body>Example Domain</body></html>",
    "https://wikipedia.org": "<html><body>Wikipedia - Free Encyclopedia</body></html>",
}


class WebBrowseTool(ToolBase):
    name = "web_browse"
    description = "Fetch the contents of a URL."

    def __init__(self, live_mode: bool = False, timeout: int = 10):
        self.live_mode = live_mode
        self.timeout = timeout

    def execute(self, url: str = "", **kwargs) -> ToolResult:
        """
        Fetch a URL and return its content.

        Parameters
        ----------
        url : str — the URL to fetch
        """
        is_harmful = classify_url_harm(url)

        if not url:
            return ToolResult(
                tool_name=self.name, success=False,
                output="No URL provided.",
                is_harmful=False,
            )

        # --- Sandbox mode: use canned responses ---
        if not self.live_mode:
            content = _CANNED_RESPONSES.get(url)
            if content is None:
                content = f"[SIMULATED] Page content for {url}"
            return ToolResult(
                tool_name=self.name, success=True,
                output=content[:5000],
                is_harmful=is_harmful,
                metadata={"url": url, "mode": "sandbox"},
            )

        # --- Live mode ---
        try:
            import requests
            resp = requests.get(url, timeout=self.timeout)
            return ToolResult(
                tool_name=self.name,
                success=(resp.status_code == 200),
                output=resp.text[:5000],
                is_harmful=is_harmful,
                metadata={
                    "url": url,
                    "status_code": resp.status_code,
                    "mode": "live",
                },
            )
        except Exception as e:
            logger.exception(f"WebBrowseTool error: {e}")
            return ToolResult(
                tool_name=self.name, success=False,
                output=f"Error: {e}",
                is_harmful=is_harmful,
            )
