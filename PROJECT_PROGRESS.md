# Agentic Safety — Project Progress (2026-03-26)

**Sources consulted:** checkpoint plan [ECE570/checkpoint1_slides_plan.md](ECE570/checkpoint1_slides_plan.md) plus current code in [agentic_safety](agentic_safety).

## Progress snapshot
- Baseline hybrid GCG+PAIR loop replicated from Checkpoint 1 and modularized in [agentic_safety/run.py](agentic_safety/run.py) and [agentic_safety/attacks/hybrid_loop.py](agentic_safety/attacks/hybrid_loop.py).
- Agentic extensions scaffolded: sandbox + tool registry ([agentic_safety/tools/sandbox.py](agentic_safety/tools/sandbox.py)) and tool implementations for file I/O, code exec, web browse, and network.
- Multi-turn Crescendo attack implemented in [agentic_safety/attacks/crescendo.py](agentic_safety/attacks/crescendo.py) with config hooks.
- Defense stack skeleton wired via [agentic_safety/defenses/registry.py](agentic_safety/defenses/registry.py) with JBShield, Gradient Cuff, Progent, StepShield classes present.
- Metrics pipeline records MIR, TIR, DBR, QTJ and exports CSV/JSON ([agentic_safety/metrics/collector.py](agentic_safety/metrics/collector.py)).
- Config presets: baseline (no sandbox/defenses), full agentic attack, and defense stress test ([agentic_safety/configs](agentic_safety/configs)).

## What is done- Judge logic updated: Rewrote Judge system prompt (`attacks/pair.py`) to mandate verifying `Tool Execution Log` for actual sandbox side-effects instead of just assuming intent equivalence. Eliminates false positives when testing smaller targets that hallucinate schema calls.
- Automated Jailbreak Dataset generation script running: Scaling dataset to 500 diverse samples explicitly formulated around OWASP Top 10 Agentic vulnerabilities (`Agentic-AI-Top10-Vulnerability` lit review material).- One-shot baseline experiments ready: `python run.py --config configs/baseline.yaml` reproduces hybrid GCG+PAIR text-only runs (Checkpoint 1 scope).
- Agentic sandbox can wrap any target model to simulate tool-use with logging of tool invocations and harm heuristics.
- Crescendo pre-check is integrated in the hybrid loop; if it jailbreaks early, the loop returns immediately.
- Metrics export with per-category summaries and time/query averages; outputs stored under configurable `output_dir` per run.

## Gaps and open issues
- No committed runs of the agentic sandbox or defense stress configs yet; only text-level baseline results exist from Checkpoint 1 (SorryBench-50 subset).
- Defense integration bug: `HybridAttackLoop` passes `DefenseResult` objects straight to the target instead of their `filtered_prompt` strings, so enabling defenses will mis-route prompts. Needs fix plus handling for blocked prompts and output filtering.
- Crescendo path is not yet routed through the sandbox/defense pipeline (no tool dispatch or defense checks during multi-turn warmup).
- DBR metric is coarse (marks any success with defenses as bypass) and does not record which defense blocked/flagged; missing granular logs.
- Tool harm detection is heuristic only; lacks judge scoring of tool outputs or alignment with plan’s “Tool Invocation Rate” for harmful actions.
- Data scale: configs still point to `sorrybench_50.json`; full SorryBench (850) and Mistral-Sorry-Bench judge are not wired or evaluated.
- Repro guidance and environment notes (models, checkpoints, hardware) are not documented inside this repo; results from Checkpoint 1 are not yet re-run via this code path.

## Next actions (suggested)
1) Fix defense pipeline wiring (use `filtered_prompt`, short-circuit on `blocked`, add response/tool checks) and rerun defense_stress.
2) Route Crescendo through sandbox/defenses and log tool calls per turn; consider passing `tool_dispatch_fn`.
3) Execute `agentic_full` with sandbox enabled to measure TIR and compare against baseline; store artifacts under `results/`.
4) Swap in full SorryBench and add Mistral-Sorry-Bench as a judge option; log per-category MIR/TIR.
5) Harden tool harm detection (judge tool outputs, refine heuristics, add allow/deny lists in Progent) and document sandbox limitations.
6) Write a short REPRO.md with setup (model paths, GPU type), run commands, and how to read CSV/JSON outputs.
