import json
import logging
from typing import Any, Dict, List, Tuple

from tools.sandbox import AgenticSandbox
from tools.file_tool import FileIOTool
from tools.code_exec import CodeExecTool
from tools.web_browse import WebBrowseTool
from tools.network_tool import NetworkTool

from .config import SandboxConfig

logger = logging.getLogger(__name__)


def build_sandbox_components(cfg: SandboxConfig) -> Tuple[Any, List[Dict[str, Any]]]:
    """Construct the sandbox and HF tool descriptors from config."""
    if not cfg.enabled:
        return None, []

    tools = []
    hf_tools: List[Dict[str, Any]] = []
    enabled_tools = cfg.tools or ["file_io", "code_exec", "web_browse", "network"]
    sandbox_root = cfg.sandbox_root

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

    return AgenticSandbox(tools=tools), hf_tools
