#!/usr/bin/env python3
"""Generate sequential GenAI Studio attack-suite jobs with dataset sharding (no GCG)."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import yaml

ATTACK_ORDER = ["pair", "crescendo", "prompt_fusion", "baseline"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create sharded attack-suite jobs for GenAI Studio")
    p.add_argument("--goals", required=True, help="Input goals JSON path")
    p.add_argument("--chunk-size", type=int, default=100, help="Goals per shard")
    p.add_argument("--model", default="genai:llama3.1:latest", help="GenAI model ID")
    p.add_argument("--rpm", type=int, default=20, help="Per-role calls/minute")
    p.add_argument("--config", default="configs/eval_genaistudio_pair_apijudge_100.yaml", help="Base config YAML")
    p.add_argument("--out-root", default="jobs/genai_attack_suite", help="Output root for jobs")
    p.add_argument("--output-dir", default="results/genai_attack_suite", help="Results output directory")
    p.add_argument("--pair-iters", type=int, default=3, help="PAIR iterations")
    p.add_argument("--crescendo-turns", type=int, default=4, help="Crescendo max turns")
    p.add_argument("--crescendo-patience", type=int, default=2, help="Crescendo patience")
    return p.parse_args()


def sanitize(s: str) -> str:
    return s.replace(":", "_").replace("/", "_")


def attacks_for(name: str, args: argparse.Namespace):
    if name == "pair":
        return [{"name": "pair", "enabled": True, "n_iterations": int(args.pair_iters)}]
    if name == "crescendo":
        return [{"name": "crescendo", "enabled": True, "max_turns": int(args.crescendo_turns), "patience": int(args.crescendo_patience)}]
    if name == "prompt_fusion":
        return [{"name": "prompt_fusion", "enabled": True, "strategy": "midpoint"}]
    if name == "baseline":
        return [{"name": "baseline", "enabled": True, "stop_on_success": False}]
    raise ValueError(f"Unknown attack {name}")


def main() -> None:
    args = parse_args()
    root = Path("/workspaces/agentic_safety")

    out_root = root / args.out_root
    shards_dir = out_root / "shards"
    configs_dir = out_root / "configs"
    scripts_dir = out_root / "scripts"
    out_root.mkdir(parents=True, exist_ok=True)
    shards_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    goals_path = root / args.goals
    with goals_path.open("r", encoding="utf-8") as f:
        goals = json.load(f)
    if not isinstance(goals, list):
        raise SystemExit("goals must be a JSON list")

    with (root / args.config).open("r", encoding="utf-8") as f:
        base = yaml.safe_load(f) or {}

    chunk = max(1, int(args.chunk_size))
    n_shards = math.ceil(len(goals) / chunk)
    shard_paths: list[Path] = []
    for i in range(n_shards):
        part = goals[i * chunk : (i + 1) * chunk]
        p = shards_dir / f"{goals_path.stem}.part_{i+1:03d}_of_{n_shards:03d}.json"
        p.write_text(json.dumps(part, indent=2), encoding="utf-8")
        shard_paths.append(p)

    model_tag = sanitize(args.model)
    script_paths: list[Path] = []

    for attack in ATTACK_ORDER:
        for idx, shard_path in enumerate(shard_paths, start=1):
            exp = f"suite_{attack}_{model_tag}_s{idx:03d}"
            cfg = dict(base)
            cfg["experiment_name"] = exp
            cfg["output_dir"] = args.output_dir
            cfg["goals_path"] = shard_path.relative_to(root).as_posix()
            cfg["wandb"] = {"enabled": False}
            cfg.setdefault("models", {})
            cfg["models"]["attack_model"] = args.model
            cfg["models"]["target_model"] = args.model
            cfg["models"]["judge_model"] = args.model
            cfg["models"]["attack_calls_per_minute"] = int(args.rpm)
            cfg["models"]["target_calls_per_minute"] = int(args.rpm)
            cfg["models"]["judge_calls_per_minute"] = int(args.rpm)
            cfg["attacks"] = attacks_for(attack, args)
            cfg_path = configs_dir / f"config_{attack}_{model_tag}_s{idx:03d}.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

            script_path = scripts_dir / f"run_{attack}_{model_tag}_s{idx:03d}.sh"
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
                "export GENAI_STUDIO_TIMEOUT_SEC=${GENAI_STUDIO_TIMEOUT_SEC:-45}",
                f"python run.py --config {cfg_path.relative_to(root).as_posix()} --verbose",
            ]
            script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            os.chmod(script_path, 0o755)
            script_paths.append(script_path)

    launcher = out_root / "run_all_suite_jobs.sh"
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
        "# Sequential execution preserves rate limits and reduces provider throttling.",
    ]
    for p in script_paths:
        launcher_lines.append(f"bash {p.relative_to(root).as_posix()}")
    launcher.write_text("\n".join(launcher_lines) + "\n", encoding="utf-8")
    os.chmod(launcher, 0o755)

    print(f"Generated {n_shards} shards from {len(goals)} goals")
    print(f"Generated {len(script_paths)} job scripts")
    print(f"Launcher: {launcher.relative_to(root).as_posix()}")


if __name__ == "__main__":
    main()
