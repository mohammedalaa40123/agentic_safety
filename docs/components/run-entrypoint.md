# run.py Entrypoint

run.py is the top-level orchestrator for experiments.

## Responsibilities

- Parse CLI overrides.
- Load and normalize YAML config.
- Build model objects for attack, target, and judge roles.
- Build optional defense registry.
- Build sandbox tool descriptors.
- Execute either attack mode or agentic mode loops.
- Record metrics and write CSV/JSON outputs.

## Important functions

- parse_args: CLI interface.
- load_goals: supports JSON arrays and CSV datasets.
- run_attack_mode: iterates goals and attack runners with defense checks.
- run_agentic_mode: iterates goals through tool-calling loop.
- main: end-to-end orchestration.

## Data contracts

- Uses AttackOutcome from runner/types.py.
- Passes outcomes to metrics.collector.MetricsCollector.
