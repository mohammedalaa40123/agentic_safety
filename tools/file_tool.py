"""
File I/O Tool — simulates an agent's ability to read/write files.

All operations are sandboxed to a temporary directory.
Tracks whether the agent attempted to access sensitive paths.
"""

from __future__ import annotations

import os
import tempfile
import logging
from typing import Optional

from .base import ToolBase, ToolResult, classify_file_harm

logger = logging.getLogger(__name__)


class FileIOTool(ToolBase):
    name = "file_io"
    description = "Read or write files in a sandboxed directory."

    def __init__(self, sandbox_root: Optional[str] = None):
        if sandbox_root is None:
            self._tmpdir = tempfile.mkdtemp(prefix="agentic_fs_")
            self.sandbox_root = self._tmpdir
        else:
            self.sandbox_root = sandbox_root
            os.makedirs(sandbox_root, exist_ok=True)

    def execute(self, action: str = "read", path: str = "", content: str = "") -> ToolResult:
        """
        Parameters
        ----------
        action : "read" | "write" | "list"
        path : str — relative path within sandbox
        content : str — content to write (for action="write")
        """
        is_harmful = classify_file_harm(path)

        # Resolve to sandbox
        safe_path = os.path.normpath(os.path.join(self.sandbox_root, path))
        if not safe_path.startswith(self.sandbox_root):
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Path traversal blocked.",
                is_harmful=True,
                metadata={"requested_path": path},
            )

        try:
            if action == "read":
                if not os.path.exists(safe_path):
                    return ToolResult(
                        tool_name=self.name, success=False,
                        output=f"File not found: {path}",
                        is_harmful=is_harmful,
                    )
                with open(safe_path, "r") as f:
                    data = f.read(10_000)  # cap at 10 KB
                return ToolResult(
                    tool_name=self.name, success=True, output=data,
                    is_harmful=is_harmful,
                    metadata={"bytes_read": len(data)},
                )

            elif action == "write":
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w") as f:
                    f.write(content)
                return ToolResult(
                    tool_name=self.name, success=True,
                    output=f"Wrote {len(content)} bytes to {path}",
                    is_harmful=is_harmful,
                    metadata={"bytes_written": len(content)},
                )

            elif action == "list":
                if not os.path.isdir(safe_path):
                    return ToolResult(
                        tool_name=self.name, success=False,
                        output=f"Not a directory: {path}",
                        is_harmful=is_harmful,
                    )
                entries = os.listdir(safe_path)[:100]
                return ToolResult(
                    tool_name=self.name, success=True,
                    output="\n".join(entries),
                    is_harmful=is_harmful,
                )

            else:
                return ToolResult(
                    tool_name=self.name, success=False,
                    output=f"Unknown action: {action}",
                    is_harmful=is_harmful,
                )

        except Exception as e:
            logger.exception(f"FileIOTool error: {e}")
            return ToolResult(
                tool_name=self.name, success=False,
                output=f"Error: {e}",
                is_harmful=is_harmful,
            )
