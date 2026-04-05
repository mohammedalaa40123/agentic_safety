# runner Package

The runner package provides thin builders and utilities that keep run.py concise.

## Files and roles

| File | Purpose |
| --- | --- |
| runner/config.py | Dataclass schema and YAML parsing with legacy compatibility. |
| runner/logging_setup.py | Run-level logging setup and header printing. |
| runner/models.py | Model factory for local HF, Gemini API, and GenAI Studio API backends. |
| runner/attacks.py | Attack runner constructors and score helpers. |
| runner/defenses.py | Defense registry construction from config. |
| runner/sandbox.py | Sandbox tool assembly and tool schema generation. |
| runner/agentic_loop.py | Iterative tool-call execution loop for agentic mode. |
| runner/types.py | Shared AttackOutcome dataclass contract. |

## Notes

- runner/models.py uses a project-local model cache under models/ by default.
- runner/config.py supports both modern nested and legacy top-level config keys.
