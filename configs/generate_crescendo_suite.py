#!/usr/bin/env python3
"""
Generate Crescendo evaluation YAML configs for all missing models.

Addresses reviewer W3: "Crescendo experiments are incomplete."

Generates configs for 7 missing models to run Crescendo on the 50-CTF dataset.
"""

import os
import yaml

# Models that need Crescendo evaluation
MISSING_MODELS = [
    ("deepseek-r1:7b", "deepseek_r1_7b"),
    ("llama3.1:latest", "llama3_1_latest"),
    ("llama3.2:latest", "llama3_2_latest"),
    ("llama3.3:70b", "llama3_3_70b"),
    ("qwen3:1.7b", "qwen3_1_7b"),
    ("qwen3:14b", "qwen3_14b"),
    ("qwen3:30b", "qwen3_30b"),
]

ATTACKER_MODEL = "llama3.3:70b"
JUDGE_MODEL = "llama3.3:70b"
DATASET = "data/agentic_scenarios_owasp_top10_50.json"

CRESCENDO_PARAMS = {
    "max_turns": 10,
    "escalation_stages": 5,
    "benign_warmup_turns": 2,
    "patience": 3,
    "context_window": 6,
}


def generate_config(target_model: str, safe_name: str) -> dict:
    """Generate a single YAML config dict."""
    return {
        "experiment_name": f"crescendo_ctf50_{safe_name}",
        "description": f"Crescendo attack evaluation on {target_model} with 50 CTF scenarios",
        "mode": "attack",
        "output_dir": f"results/crescendo_ctf50/{safe_name}",
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
                "name": "crescendo",
                "enabled": True,
                "stop_on_success": False,
                "params": CRESCENDO_PARAMS,
            }
        ],
        "defenses": {
            "enabled": False,
            "active": [],
        },
        "logging": {
            "verbose": True,
        },
    }


def main():
    configs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
    os.makedirs(configs_dir, exist_ok=True)

    generated = []
    for target_model, safe_name in MISSING_MODELS:
        config = generate_config(target_model, safe_name)
        filename = f"eval_crescendo_ctf50_{safe_name}.yaml"
        filepath = os.path.join(configs_dir, filename)

        with open(filepath, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        generated.append(filepath)
        print(f"  Generated: {filename}")

    print(f"\nGenerated {len(generated)} Crescendo configs.")
    print("\nTo run all jobs:")
    for fp in generated:
        rel = os.path.relpath(fp)
        print(f"  python run.py --config {rel}")

    # Also generate a shell script for batch submission
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "scripts",
        "run_crescendo_suite.sh",
    )
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Auto-generated: run all Crescendo CTF-50 evaluations\n")
        f.write("set -e\n\n")
        for fp in generated:
            rel = os.path.relpath(fp)
            f.write(f'echo "=== Running {os.path.basename(fp)} ==="\n')
            f.write(f"python run.py --config {rel}\n\n")
    os.chmod(script_path, 0o755)
    print(f"\nBatch script: {os.path.relpath(script_path)}")


if __name__ == "__main__":
    main()
