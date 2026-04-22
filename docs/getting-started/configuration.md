# Configuration

Experiment configuration is loaded from YAML and parsed by `runner/config.py`.

## Core sections

- `experiment_name`: human-readable run label.
- `description`: free-form description for the run.
- `mode`: `attack`, `baseline`, or `agentic`.
- `output_dir`: where logs and result files are written.
- `goals_path`: path to goals dataset in JSON or CSV format.

## Models section

- `attack_model`: model used by attack runners.
- `target_model`: model used for expected-response generation.
- `judge_model`: model used for score/judge evaluation.
- `attack_max_n_tokens`, `target_max_n_tokens`, `judge_max_n_tokens`: generation limits.
- `attack_calls_per_minute`, `target_calls_per_minute`, `judge_calls_per_minute`: rate-limit values.

## Sandbox section

- `enabled`: enable sandbox tool execution.
- `sandbox_root`: host directory mounted inside the sandbox.
- `tools`: list of enabled tools: `file_io`, `code_exec`, `web_browse`, `network`.
- `code_timeout`, `web_timeout`: tool execution timeouts.
- `code_exec_backend`: `auto`, `bwrap`, or `none`.
- `code_exec_require_isolation`: fail closed if isolation cannot be provided.
- `net_sandbox`, `web_sandbox`: choose network/web modes.
- `max_steps`: maximum tool-action turns for agentic evaluation.

## Attacks section

Attack definitions are ordered and support:

- `name`
- `enabled`
- `stop_on_success`
- `params`

Example:

```yaml
attacks:
  - name: pair
    enabled: true
    stop_on_success: true
    params:
      n_iterations: 1
```

## Defenses section

- `enabled`: global defense toggle.
- `active`: enabled defense names.
- `jbshield`, `gradient_cuff`, `progent`, `stepshield`: per-defense parameters.

Example:

```yaml
defenses:
  enabled: true
  active: [jbshield, progent]
  jbshield:
    threshold: 0.8
```

## Logging and tracking

- `wandb.enabled`: enable Weights & Biases logging.
- `wandb.project`, `wandb.entity`, `wandb.run_name`: W&B metadata.
- `logging.verbose`: enable debug logs.

## Goal dataset formats

- JSON: array of objects with `goal`, `target`, and `category`.
- CSV: rows containing `goal` or `prompt`, `target` or `target_str`, and `category`.

## CLI override behavior

Run `run.py --help` for the latest override options.
CLI flags such as `--mode`, `--goals`, `--attack-model`, and `--use-defenses` take precedence over YAML values.
