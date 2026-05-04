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
        self._docker_path = shutil.which("docker")
        self._docker_daemon_ok: bool | None = None  # lazily checked
        self._bwrap_functional: bool | None = None  # lazily tested at runtime
        if sandbox_root is None:
            self._tmpdir = tempfile.mkdtemp(prefix="agentic_code_")
            self.sandbox_root = self._tmpdir
        else:
            self.sandbox_root = sandbox_root
            os.makedirs(sandbox_root, exist_ok=True)

    def _docker_available(self) -> bool:
        """Return True only if the docker binary exists AND the daemon is reachable."""
        if not self._docker_path:
            return False
        if self._docker_daemon_ok is None:
            try:
                import subprocess as _sp
                result = _sp.run(
                    [self._docker_path, "info"],
                    capture_output=True, timeout=3,
                )
                self._docker_daemon_ok = (result.returncode == 0)
            except Exception:
                self._docker_daemon_ok = False
        return self._docker_daemon_ok

    def _bwrap_available(self) -> bool:
        """Return True only if bwrap exists AND can actually execute in this environment."""
        if not self._bwrap_path:
            return False
        if self._bwrap_functional is None:
            try:
                result = subprocess.run(
                    [self._bwrap_path, "--unshare-net", "--tmpfs", "/tmp",
                     "--ro-bind", "/usr", "/usr",
                     shutil.which("true") or "/bin/true"],
                    capture_output=True, timeout=5,
                )
                self._bwrap_functional = (result.returncode == 0)
                if not self._bwrap_functional:
                    logger.warning(
                        "[CodeExec] bwrap probe failed (rc=%d): %s — "
                        "will fall back to docker or local backend.",
                        result.returncode, result.stderr[:200],
                    )
            except Exception as exc:
                self._bwrap_functional = False
                logger.warning("[CodeExec] bwrap probe exception: %s — disabling bwrap.", exc)
        return self._bwrap_functional

    def _effective_backend(self) -> str:
        if self.isolation_backend in {"none", "local"}:
            return "local"
        if self.isolation_backend == "bwrap":
            return "bwrap" if self._bwrap_available() else "missing"
        if self.isolation_backend == "docker":
            return "docker" if self._docker_available() else "missing"
        if self.isolation_backend == "auto":
            # Prefer bwrap (Linux), fall back to docker if daemon is running, else local
            if self._bwrap_available():
                return "bwrap"
            if self._docker_available():
                return "docker"
            return "local"   # no isolation available — run in-process sandbox
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

    def _build_docker_cmd(self, script_path: str) -> list[str]:
        if not self._docker_path:
            raise RuntimeError("docker executable not found")
        return [
            self._docker_path, "run",
            "--rm",
            "--network", "none",
            "--memory", "256m",
            "--memory-swap", "256m",
            "--cpus", "0.5",
            "--read-only",
            "--tmpfs", "/tmp",
            "-v", f"{self.sandbox_root}:/work:rw",
            "-w", "/work",
            "--security-opt", "no-new-privileges",
            "python:3.11-slim",
            "python3", f"/work/{os.path.basename(script_path)}",
        ]

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
            # Network and IPC isolation (no user namespace needed for these)
            "--unshare-net",
            "--unshare-ipc",
            "--unshare-uts",
            # Use tmpfs for /proc and /tmp — avoids mounting real procfs (which
            # requires user namespaces unavailable in HF Space / unprivileged containers).
            "--tmpfs", "/proc",
            "--tmpfs", "/tmp",
            "--dir", "/work",
            "--bind", self.sandbox_root, "/work",
            "--chdir", "/work",
            "--setenv", "HOME", "/work",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        ]

        # Bind essential /dev files individually (avoids --dev which needs mount privs)
        for dev_node in ["/dev/null", "/dev/zero", "/dev/urandom", "/dev/random"]:
            if os.path.exists(dev_node):
                cmd.extend(["--bind", dev_node, dev_node])

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
        backend = self._effective_backend()

        # Hard block obviously harmful patterns so we don't touch host files IF NOT isolated.
        if is_harmful and backend == "local":
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Blocked potentially harmful code (os/system/rm/requests/socket) in local backend.",
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
                output="Blocked: no command isolation backend available (bwrap or docker required).",
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
            elif backend == "docker":
                cmd = self._build_docker_cmd(script_path)
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 30,  # extra time for container spin-up
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
