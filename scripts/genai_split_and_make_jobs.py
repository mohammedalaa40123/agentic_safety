#!/usr/bin/env python3
"""Split a goals JSON file and generate one run script per shard/model.

Example:
  python scripts/genai_split_and_make_jobs.py \
    --goals data/agentic_scenarios_asr_eval_v2.json \
    --chunk-size 100 \
    --models genai:llama3.1:latest genai:llama3.3:70b genai:deepseek-r1:14b \
    --out-root jobs/genai_shards
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split goals and create shard run scripts")
    p.add_argument("--goals", required=True, help="Input goals JSON array")
    p.add_argument("--chunk-size", type=int, default=100, help="Items per shard")
    p.add_argument("--models", nargs="+", required=True, help="GenAI model IDs, e.g. genai:llama3.3:70b")
    p.add_argument("--out-root", default="jobs/genai_shards", help="Output root directory")
    p.add_argument("--config", default="configs/eval_genaistudio_pair_apijudge_100.yaml", help="Base config path")
    p.add_argument("--iterations", type=int, default=5, help="PAIR n_iterations")
    p.add_argument("--rpm", type=int, default=20, help="Per-role calls/minute cap")
    p.add_argument("--output-dir", default="results/genai_shards", help="Evaluation output directory")
    return p.parse_args()


def sanitize_model(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def main() -> None:
    args = parse_args()

    goals_path = Path(args.goals)
    out_root = Path(args.out_root)
    shards_dir = out_root / "shards"
    scripts_dir = out_root / "scripts"
    configs_dir = out_root / "configs"

    out_root.mkdir(parents=True, exist_ok=True)
    shards_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)

    with open(args.config, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f) or {}

    with goals_path.open("r", encoding="utf-8") as f:
        goals = json.load(f)

    if not isinstance(goals, list):
        raise SystemExit("Input goals must be a JSON array")
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be > 0")

    total = len(goals)
    n_shards = math.ceil(total / args.chunk_size)

    shard_paths: list[Path] = []
    for i in range(n_shards):
        start = i * args.chunk_size
        end = min(start + args.chunk_size, total)
        shard = goals[start:end]
        shard_path = shards_dir / f"{goals_path.stem}.part_{i+1:03d}_of_{n_shards:03d}.json"
        with shard_path.open("w", encoding="utf-8") as f:
            json.dump(shard, f, ensure_ascii=True, indent=2)
        shard_paths.append(shard_path)

    all_jobs = []
    for model in args.models:
        model_tag = sanitize_model(model)
        for idx, shard_path in enumerate(shard_paths, start=1):
            script_name = f"run_{model_tag}_shard_{idx:03d}.sh"
            script_path = scripts_dir / script_name
            run_name = f"genai_{model_tag}_s{idx:03d}"
            cfg_path = configs_dir / f"config_{model_tag}_shard_{idx:03d}.yaml"

            cfg = dict(base_cfg)
            cfg["experiment_name"] = run_name
            cfg.setdefault("models", {})
            cfg["models"]["attack_model"] = model
            cfg["models"]["target_model"] = model
            cfg["models"]["judge_model"] = model
            cfg["models"]["attack_calls_per_minute"] = int(args.rpm)
            cfg["models"]["target_calls_per_minute"] = int(args.rpm)
            cfg["models"]["judge_calls_per_minute"] = int(args.rpm)

            attacks = cfg.get("attacks") or []
            if isinstance(attacks, list) and attacks:
                pair_found = False
                for a in attacks:
                    if isinstance(a, dict) and (a.get("name") or "").lower() == "pair":
                        a["enabled"] = True
                        a["n_iterations"] = int(args.iterations)
                        pair_found = True
                    elif isinstance(a, dict) and "enabled" in a:
                        a["enabled"] = False
                if not pair_found:
                    attacks.insert(0, {"name": "pair", "enabled": True, "n_iterations": int(args.iterations)})
            else:
                cfg["attacks"] = [{"name": "pair", "enabled": True, "n_iterations": int(args.iterations)}]

            with cfg_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)

            lines = [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "if [[ -z \"${GENAI_STUDIO_API_KEY:-}\" ]]; then",
                "  echo \"GENAI_STUDIO_API_KEY is not set\" >&2",
                "  exit 1",
                "fi",
                "",
                "cd /workspaces/agentic_safety",
                f"mkdir -p {args.output_dir}",
                "",
                "python run.py \\",
                f"  --config {cfg_path.as_posix()} \\",
                f"  --goals {shard_path.as_posix()} \\",
                f"  --output-dir {args.output_dir} \\",
                "  --attack-plan pair \\",
                "  --mode attack \\",
                "  --verbose",
            ]
            script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            os.chmod(script_path, 0o755)
            all_jobs.append((model, idx, script_path))

    launcher = out_root / "run_all_generated_jobs.sh"
    launcher_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "if [[ -z \"${GENAI_STUDIO_API_KEY:-}\" ]]; then",
        "  echo \"GENAI_STUDIO_API_KEY is not set\" >&2",
        "  exit 1",
        "fi",
        "",
        "cd /workspaces/agentic_safety",
        "",
        "# Keep to 20 req/min cap per role; do not run these scripts in parallel.",
        "# If your account is strict globally, consider reducing rpm in your base YAML as well.",
    ]

    for _, _, script_path in all_jobs:
        launcher_lines.append(f"bash {script_path.as_posix()}")

    launcher.write_text("\n".join(launcher_lines) + "\n", encoding="utf-8")
    os.chmod(launcher, 0o755)

    print(f"Wrote {len(shard_paths)} shard files to: {shards_dir}")
    print(f"Wrote {len(all_jobs)} job scripts to: {scripts_dir}")
    print(f"Launcher: {launcher}")
    print(f"Total goals: {total}; chunk size: {args.chunk_size}; shards: {n_shards}")


if __name__ == "__main__":
    main()
