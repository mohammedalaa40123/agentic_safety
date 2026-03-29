"""
Code Execution Tool — simulates an agent's ability to run Python code.

Executes code in a restricted subprocess with timeout enforcement.
Tracks whether the code contains harmful operations.
"""

from __future__ import annotations

import subprocess
import tempfile
import os
import logging
from typing import Optional

from .base import ToolBase, ToolResult, classify_code_harm

logger = logging.getLogger(__name__)


class CodeExecTool(ToolBase):
    name = "code_exec"
    description = "Execute a Python code snippet in a sandboxed subprocess."

    def __init__(
        self,
        timeout: int = 10,
        python_path: str = "python3",
        sandbox_root: Optional[str] = None,
    ):
        self.timeout = timeout
        self.python_path = python_path
        if sandbox_root is None:
            self._tmpdir = tempfile.mkdtemp(prefix="agentic_code_")
            self.sandbox_root = self._tmpdir
        else:
            self.sandbox_root = sandbox_root
            os.makedirs(sandbox_root, exist_ok=True)

    def execute(self, code: str = "", **kwargs) -> ToolResult:
        """
        Run a Python snippet and capture stdout/stderr.

        Parameters
        ----------
        code : str — Python source code to execute
        """
        is_harmful = classify_code_harm(code)

        # Normalize escaped newlines/tabs that frequently arrive from JSON tool calls
        if isinstance(code, str):
            if "\\n" in code:
                code = code.replace("\\n", "\n")
            if "\\t" in code:
                code = code.replace("\\t", "\t")
            # Trim stray carriage returns to keep line numbers clean
            code = code.replace("\r\n", "\n")

        # Write code to a temp file inside sandbox
        script_path = os.path.join(self.sandbox_root, "_agent_script.py")
        with open(script_path, "w") as f:
            f.write(code)

        try:
            proc = subprocess.run(
                [self.python_path, script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.sandbox_root,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin"),
                    "HOME": self.sandbox_root,
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            output = proc.stdout[:5000]
            if proc.stderr:
                output += f"\n[STDERR]: {proc.stderr[:2000]}"

            return ToolResult(
                tool_name=self.name,
                success=(proc.returncode == 0),
                output=output,
                is_harmful=is_harmful,
                metadata={
                    "returncode": proc.returncode,
                    "code_length": len(code),
                },
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output=f"Timeout after {self.timeout}s",
                is_harmful=is_harmful,
                metadata={"timeout": self.timeout},
            )
        except Exception as e:
            logger.exception(f"CodeExecTool error: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                output=f"Error: {e}",
                is_harmful=is_harmful,
            )
        finally:
            # Cleanup
            if os.path.exists(script_path):
                os.remove(script_path)
