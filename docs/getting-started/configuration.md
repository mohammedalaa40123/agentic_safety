# Configuration

Configuration is loaded from YAML and parsed by runner/config.py.

## Core sections

- experiment_name: Human-readable run label.
- description: Free-form run description.
- mode: attack, baseline, or agentic.
- output_dir: Output path for logs and metrics.
- goals_path: JSON/CSV dataset path.

## models section

- attack_model: Model used by attacker loop.
- target_model: Model used to generate target responses.
- judge_model: Model used for judge scoring.
- attack_max_n_tokens, target_max_n_tokens, judge_max_n_tokens: generation limits.
- attack_calls_per_minute, target_calls_per_minute, judge_calls_per_minute: role-specific rate limits.

## sandbox section

- enabled: Toggle sandbox tool execution.
- sandbox_root: Host directory mounted for sandbox operations.
- tools: enabled tools list (file_io, code_exec, web_browse, network).
- code_timeout, web_timeout: tool timeout controls.
- code_exec_backend: auto, bwrap, or none.
- code_exec_require_isolation: fail closed when no isolation backend exists.
- net_sandbox, web_sandbox: choose live versus simulated behavior.
- max_steps: max tool-action turns in agentic loop.

## attacks section

Attacks are ordered and each entry supports:

- name
- enabled
- stop_on_success
- params

## defenses section

- enabled: global defense toggle.
- active: list of enabled defense names.
- jbshield, gradient_cuff, progent, stepshield: per-defense parameter blocks.

## wandb and logging sections

- wandb.enabled and related metadata fields.
- logging.verbose for debug-level logs.
