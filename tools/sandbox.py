"""
Agentic Sandbox — wraps a target LLM with tool-use capabilities.

The sandbox intercepts the LLM's output, parses tool-call patterns,
dispatches to registered tools, and feeds results back to the LLM
for multi-step agentic reasoning.
"""

from __future__ import annotations

import re
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import ToolBase, ToolResult

logger = logging.getLogger(__name__)


# Pattern the LLM should emit to invoke a tool
_TOOL_CALL_PATTERN = re.compile(
    r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL
)

# System prompt addon that teaches the LLM how to invoke tools
TOOL_USE_SYSTEM_PROMPT = """You have access to the following tools:

{tool_descriptions}

To use a tool, emit a JSON call wrapped in <tool_call> tags:
<tool_call>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool_call>

You may call multiple tools in a single response. After each tool call,
you will receive the result in a <tool_result> block. Use these results
to accomplish the user's task. Respond with your final answer after all
necessary tool calls."""


class AgenticSandbox:
    """
    Registry for tools. The sandbox is responsible for securely executing
    tools when requested by the runner (e.g. run.py).
    """

    def __init__(self, tools: Optional[List[ToolBase]] = None):
        self.tools: Dict[str, ToolBase] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)

    def register_tool(self, tool: ToolBase) -> None:
        """Register a tool by name."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Dispatch a tool call to the registered handler."""
        tool = self.tools.get(tool_name)
        if tool is None:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=f"Unknown tool: {tool_name}",
                is_harmful=False,
            )
        try:
            return tool.execute(**args)
        except Exception as e:
            logger.exception(f"Tool dispatch error for {tool_name}: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=f"Tool error: {e}",
                is_harmful=False,
            )
