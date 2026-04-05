"""
Code Execution Tool — simulates an agent's ability to run Python code.

Executes code in a restricted subprocess with timeout enforcement.
Tracks whether the code contains harmful operations.
"""

from __future__ import annotations

import subprocess
import tempfile
import os
import shutil
import resource
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
        isolation_backend: str = "auto",
        require_isolation: bool = True,
    ):
        self.timeout = timeout
        self.python_path = python_path
        self.isolation_backend = (isolation_backend or "auto").lower()
        self.require_isolation = bool(require_isolation)
        self._bwrap_path = shutil.which("bwrap")
        if sandbox_root is None:
            self._tmpdir = tempfile.mkdtemp(prefix="agentic_code_")
            self.sandbox_root = self._tmpdir
        else:
            self.sandbox_root = sandbox_root
            os.makedirs(sandbox_root, exist_ok=True)

    def _effective_backend(self) -> str:
        if self.isolation_backend in {"none", "local"}:
            return "local"
        if self.isolation_backend == "bwrap":
            return "bwrap" if self._bwrap_path else "missing"
        if self.isolation_backend == "auto":
            return "bwrap" if self._bwrap_path else "missing"
        return "missing"

    def _set_limits(self) -> None:
        # Bound CPU, memory, and output file size to keep runs contained.
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout + 1, self.timeout + 1))
        except Exception:
            pass
        try:
            mem_limit = 512 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
        except Exception:
            pass
        try:
            file_limit = 10 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        except Exception:
            pass

    def _build_bwrap_cmd(self, script_path: str) -> list[str]:
        if not self._bwrap_path:
            raise RuntimeError("bwrap executable not found")

        py_exec = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else shutil.which("python3")
        if not py_exec:
            raise RuntimeError("No python3 executable found for isolated execution")

        cmd = [
            self._bwrap_path,
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
            "--unshare-net",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--dir",
            "/work",
            "--bind",
            self.sandbox_root,
            "/work",
            "--chdir",
            "/work",
            "--setenv",
            "HOME",
            "/work",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
        ]

        ro_paths = ["/usr", "/bin", "/lib", "/lib64"]
        for path in ro_paths:
            if os.path.exists(path):
                cmd.extend(["--ro-bind", path, path])

        # Bind our mock OS directories if they exist in the sandbox_root
        mock_etc = os.path.join(self.sandbox_root, "etc")
        if os.path.exists(mock_etc):
            cmd.extend(["--ro-bind", mock_etc, "/etc"])
        elif os.path.exists("/etc"):
            cmd.extend(["--ro-bind", "/etc", "/etc"])
            
        mock_var_log = os.path.join(self.sandbox_root, "var", "log")
        if os.path.exists(mock_var_log):
            cmd.extend(["--bind", mock_var_log, "/var/log"])

        cmd.extend([py_exec, f"/work/{os.path.basename(script_path)}"])
        return cmd

    def execute(self, code: str = "", **kwargs) -> ToolResult:
        """
        Run a Python snippet and capture stdout/stderr.

        Parameters
        ----------
        code : str — Python source code to execute
        """
        is_harmful = classify_code_harm(code)

        # Hard block obviously harmful patterns so we don't touch host files.
        if is_harmful:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Blocked potentially harmful code (os/system/rm/requests/socket).",
                is_harmful=True,
                metadata={"blocked": True},
            )

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

        backend = self._effective_backend()
        if backend == "missing" and self.require_isolation:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Blocked: no command isolation backend available (bwrap required).",
                is_harmful=is_harmful,
                metadata={"blocked": True, "reason": "missing_isolation_backend"},
            )

        try:
            if backend == "bwrap":
                cmd = self._build_bwrap_cmd(script_path)
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=self.sandbox_root,
                    preexec_fn=self._set_limits,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "HOME": "/work",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )
            else:
                proc = subprocess.run(
                    [self.python_path, script_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=self.sandbox_root,
                    preexec_fn=self._set_limits,
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
                    "backend": backend,
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
