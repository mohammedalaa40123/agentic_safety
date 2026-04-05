# attacks Package

The attacks package contains attack loops and prompt optimization strategies.

## Core attack files

| File | Purpose |
| --- | --- |
| attacks/pair.py | PAIR attack loop and judge prompt handling. |
| attacks/gcg.py | GCG-based optimization loop integration. |
| attacks/crescendo.py | Multi-turn escalation attack strategy. |
| attacks/prompt_fusion.py | Prompt fusion strategies for combining generated candidates. |
| attacks/hybrid_loop.py | Combined orchestration of PAIR, GCG, fusion, and optional Crescendo. |
| attacks/__init__.py | Package exports. |

## Threat reference folder

attacks/Agentic-AI-Top10-Vulnerability contains 16 markdown references plus README for vulnerability taxonomy and examples.

## Coverage intent

Attack modules are designed to be independently pluggable via the attacks list in config.
