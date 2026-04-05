# tools Package

The tools package defines sandboxed tool primitives and the sandbox dispatcher.

## Files and roles

| File | Purpose |
| --- | --- |
| tools/base.py | Tool base class, ToolResult, and harm classification helpers. |
| tools/sandbox.py | AgenticSandbox dispatcher and execution wiring. |
| tools/file_tool.py | Sandboxed file read/write/list operations. |
| tools/code_exec.py | Python code execution with timeout and optional bwrap isolation. |
| tools/web_browse.py | URL fetch in live or sandboxed mode. |
| tools/network_tool.py | Network simulation or restricted live actions. |
| tools/__init__.py | Package exports. |

## Safety behavior

- Harmful code patterns are blocked before execution in code_exec.
- Isolation backend can fail closed when configured.
- Tool outputs are truncated in logs to reduce prompt explosion.
