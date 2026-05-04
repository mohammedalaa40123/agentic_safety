#!/usr/bin/env python3
"""
Generate Defense evaluation YAML configs for the defense-by-attack matrix.

Addresses reviewer W4: "Defenses are implemented but not evaluated."

Generates a 4 defenses × 2 attacks × 3 models = 24-cell evaluation matrix.
Each config runs 50 CTF scenarios with a specific defense enabled.
"""

import os
import yaml

# Defense configurations
DEFENSES = {
    "agentshield": {
        "name": "agentshield",
        "layer": "input",
        "config": {
            "threshold": 0.7,
        },
    },
    "stepshield": {
        "name": "stepshield",
        "layer": "multi-layer",
        "config": {
            "step_threshold": 0.6,
        },
    },
    "progent": {
        "name": "progent",
        "layer": "tool-policy",
        "config": {
            "policy_mode": "strict",
        },
    },
    "contextguard": {
        "name": "contextguard",
        "layer": "input",
        "config": {
            "model_name": None,  # uses target_fn by default
        },
    },
}

# Attack configurations
ATTACKS = {
    "pair": {
        "name": "pair",
        "params": {
            "n_iterations": 5,
        },
    },
    "crescendo": {
        "name": "crescendo",
        "params": {
            "max_turns": 10,
            "escalation_stages": 5,
            "benign_warmup_turns": 2,
            "patience": 3,
            "context_window": 6,
        },
    },
}

# Target models (3 representative: high, high, moderate vulnerability)
MODELS = [
    ("deepseek-r1:14b", "deepseek_r1_14b"),
    ("llama3.3:70b", "llama3_3_70b"),
    ("qwen3:14b", "qwen3_14b"),
]

ATTACKER_MODEL = "llama3.3:70b"
JUDGE_MODEL = "llama3.3:70b"
DATASET = "data/agentic_scenarios_owasp_top10_50.json"


def generate_config(
    target_model: str,
    model_safe: str,
    attack_name: str,
    attack_params: dict,
    defense_name: str,
    defense_config: dict,
) -> dict:
    """Generate a single defense evaluation YAML config."""
    return {
        "experiment_name": f"defense_{defense_name}_{attack_name}_{model_safe}",
        "description": (
            f"Defense evaluation: {defense_name} against {attack_name} "
            f"on {target_model} (50 CTF scenarios)"
        ),
        "mode": "attack",
        "output_dir": f"results/defense_eval/{defense_name}/{attack_name}_{model_safe}",
        "goals_path": DATASET,
        "models": {
            "attack_model": f"genai:{ATTACKER_MODEL}",
            "target_model": f"genai:{target_model}",
            "judge_model": f"genai:{JUDGE_MODEL}",
            "attack_max_n_tokens": 2048,
            "target_max_n_tokens": 1024,
            "judge_max_n_tokens": 1024,
            "attack_calls_per_minute": 20,
            "target_calls_per_minute": 20,
            "judge_calls_per_minute": 20,
        },
        "sandbox": {
            "enabled": True,
            "persistent": True,
            "tools": ["file_io", "code_exec", "web_browse", "network"],
            "max_steps": 5,
        },
        "attacks": [
            {
                "name": attack_name,
                "enabled": True,
                "stop_on_success": False,
                "params": attack_params,
            }
        ],
        "defenses": {
            "enabled": True,
            "active": [defense_name],
            defense_name: defense_config,
        },
        "logging": {
            "verbose": True,
        },
    }


def main():
    configs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "defense_eval")
    os.makedirs(configs_dir, exist_ok=True)

    generated = []
    for defense_name, defense_info in DEFENSES.items():
        for attack_name, attack_info in ATTACKS.items():
            for target_model, model_safe in MODELS:
                config = generate_config(
                    target_model=target_model,
                    model_safe=model_safe,
                    attack_name=attack_name,
                    attack_params=attack_info["params"],
                    defense_name=defense_name,
                    defense_config=defense_info["config"],
                )
                filename = f"eval_{defense_name}_{attack_name}_{model_safe}.yaml"
                filepath = os.path.join(configs_dir, filename)

                with open(filepath, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                generated.append(filepath)

    print(f"Generated {len(generated)} defense evaluation configs:")
    print(f"  {len(DEFENSES)} defenses × {len(ATTACKS)} attacks × {len(MODELS)} models")
    print()

    # Summary matrix
    print("Defense × Attack × Model Matrix:")
    print(f"{'Defense':<15} {'Attack':<12} {'Model':<20} Config")
    print("-" * 80)
    for fp in generated:
        basename = os.path.basename(fp).replace("eval_", "").replace(".yaml", "")
        parts = basename.split("_")
        print(f"  {basename}")

    # Generate batch script
    script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    os.makedirs(script_dir, exist_ok=True)
    script_path = os.path.join(script_dir, "run_defense_suite.sh")

    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Auto-generated: run all defense evaluation configs\n")
        f.write("# 4 defenses × 2 attacks × 3 models = 24 jobs\n")
        f.write("set -e\n\n")

        for fp in generated:
            rel = os.path.relpath(fp)
            f.write(f'echo "=== {os.path.basename(fp)} ==="\n')
            f.write(f"python run.py --config {rel}\n\n")

    os.chmod(script_path, 0o755)
    print(f"\nBatch script: {os.path.relpath(script_path)}")

    # Also generate a "no defense" baseline for the same 3 models × 2 attacks
    baseline_dir = os.path.join(configs_dir, "baselines")
    os.makedirs(baseline_dir, exist_ok=True)
    print(f"\nAlso generating no-defense baseline configs for comparison...")
    for attack_name, attack_info in ATTACKS.items():
        for target_model, model_safe in MODELS:
            config = {
                "experiment_name": f"defense_none_{attack_name}_{model_safe}",
                "description": f"No-defense baseline: {attack_name} on {target_model}",
                "mode": "attack",
                "output_dir": f"results/defense_eval/none/{attack_name}_{model_safe}",
                "goals_path": DATASET,
                "models": {
                    "attack_model": f"genai:{ATTACKER_MODEL}",
                    "target_model": f"genai:{target_model}",
                    "judge_model": f"genai:{JUDGE_MODEL}",
                    "attack_max_n_tokens": 2048,
                    "target_max_n_tokens": 1024,
                    "judge_max_n_tokens": 1024,
                    "attack_calls_per_minute": 20,
                    "target_calls_per_minute": 20,
                    "judge_calls_per_minute": 20,
                },
                "sandbox": {
                    "enabled": True,
                    "persistent": True,
                    "tools": ["file_io", "code_exec", "web_browse", "network"],
                    "max_steps": 5,
                },
                "attacks": [
                    {
                        "name": attack_name,
                        "enabled": True,
                        "stop_on_success": False,
                        "params": attack_info["params"],
                    }
                ],
                "defenses": {"enabled": False, "active": []},
                "logging": {"verbose": True},
            }
            filename = f"eval_none_{attack_name}_{model_safe}.yaml"
            filepath = os.path.join(baseline_dir, filename)
            with open(filepath, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print(f"  Generated baseline: {filename}")


if __name__ == "__main__":
    main()
