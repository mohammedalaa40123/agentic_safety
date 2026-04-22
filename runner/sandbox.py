import json
import logging
from typing import Any, Dict, List, Tuple

from tools.sandbox import AgenticSandbox
from tools.file_tool import FileIOTool
from tools.code_exec import CodeExecTool
from tools.web_browse import WebBrowseTool
from tools.network_tool import NetworkTool

from .config import SandboxConfig
from .sandbox_init import init_sandbox_fixtures, reset_sandbox_fixtures

logger = logging.getLogger(__name__)

# Module-level cache: sandbox_root → (AgenticSandbox, hf_tools)
# Populated on the first call when persistent=True; subsequent calls return
# the same objects so the filesystem state is kept alive across goals/attacks.
_SANDBOX_CACHE: Dict[str, Tuple[Any, List[Dict[str, Any]]]] = {}


def build_sandbox_components(cfg: SandboxConfig) -> Tuple[Any, List[Dict[str, Any]]]:
    """Construct the sandbox and HF tool descriptors from config.

    When ``cfg.persistent`` is True (the default) the sandbox directory is
    initialised with fixture files exactly once and the same
    ``AgenticSandbox`` instance is returned on every subsequent call — no
    Docker restart, no directory wipe between goals.

    When ``cfg.persistent`` is False a fresh sandbox is built every call
    (original behaviour, useful for isolation testing).
    """
    if not cfg.enabled:
        return None, []

    sandbox_root = cfg.sandbox_root

    # ── persistent mode: return cached instance if already built ──────────
    if cfg.persistent and sandbox_root in _SANDBOX_CACHE:
        return _SANDBOX_CACHE[sandbox_root]

    # ── initialise fixture files once ─────────────────────────────────────
    if cfg.persistent:
        init_sandbox_fixtures(sandbox_root)
    else:
        # Non-persistent: always start fresh
        reset_sandbox_fixtures(sandbox_root)

    # ── build tool objects ─────────────────────────────────────────────────
    tools = []
    hf_tools: List[Dict[str, Any]] = []
    enabled_tools = cfg.tools or ["file_io", "code_exec", "web_browse", "network"]

    if "file_io" in enabled_tools:
        tools.append(FileIOTool(sandbox_root=sandbox_root))
        hf_tools.append({
            "type": "function",
            "function": {
                "name": "file_io",
                "description": "Read, write, or list files in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["read", "write", "list"], "description": "File operation"},
                        "path": {"type": "string", "description": "Relative file path within sandbox"},
                        "content": {"type": "string", "description": "Content to write (only for write action)"},
                    },
                    "required": ["action"],
                },
            },
        })

    if "code_exec" in enabled_tools:
        tools.append(
            CodeExecTool(
                timeout=cfg.code_timeout,
                sandbox_root=sandbox_root,
                isolation_backend=cfg.code_exec_backend,
                require_isolation=cfg.code_exec_require_isolation,
            )
        )
        hf_tools.append({
            "type": "function",
            "function": {
                "name": "code_exec",
                "description": "Run a Python snippet and capture stdout/stderr.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                    },
                    "required": ["code"],
                },
            },
        })

    if "web_browse" in enabled_tools:
        web_live = not cfg.web_sandbox
        tools.append(WebBrowseTool(live_mode=web_live, timeout=cfg.web_timeout))
        hf_tools.append({
            "type": "function",
            "function": {
                "name": "web_browse",
                "description": "Fetch a URL and return its content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to fetch"},
                    },
                    "required": ["url"],
                },
            },
        })

    if "network" in enabled_tools:
        net_live = not cfg.net_sandbox
        tools.append(NetworkTool(live_mode=net_live))
        hf_tools.append({
            "type": "function",
            "function": {
                "name": "network",
                "description": "Perform network operations like ping or DNS lookup.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["ping", "dns_lookup", "port_scan"], "description": "Network operation"},
                        "host": {"type": "string", "description": "Hostname or IP address"},
                        "port": {"type": "integer", "description": "Port number (only for port_scan action)"},
                    },
                    "required": ["action", "host"],
                },
            },
        })

    tool_names = [t.name for t in tools]
    result = AgenticSandbox(tools=tools), hf_tools
    logger.info("[SANDBOX] Initialized — registered tools: %s (persistent=%s)", tool_names, cfg.persistent)

    if cfg.persistent:
        _SANDBOX_CACHE[sandbox_root] = result

    return result

