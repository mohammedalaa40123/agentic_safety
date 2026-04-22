#!/usr/bin/env python3
"""
Deploy the Agentic Safety Evaluator to a private HuggingFace Space.

Usage:
    python scripts/deploy_hf_space.py \
        --repo <owner>/<space-name> \
        --token <hf-write-token>   # or set HF_TOKEN env var

The Space will be created (or updated) as:
  - SDK : docker  (uses the repo's Dockerfile)
  - Visibility : private
  - Port : 7860  (set in README.md frontmatter and Dockerfile)
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Paths / patterns to exclude from the upload (keeps the Space lean)
IGNORE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    ".venv",
    ".venv/**",
    "node_modules",
    "node_modules/**",
    "frontend/node_modules/**",
    "*.log",
    "nohup.out",
    "results/**",
    "wandb/**",
    "agentic_experiments_v2_500*/**",
    "agentic_experiments_v2_500 copy/**",
    "jobs/**",
    "tmp*.yaml",
    ".git",
    ".git/**",
    "site/**",
    # data/ — only expose the 50-sample OWASP eval dataset; hide everything else
    "data/gcg_cache_*.json",
    "data/owasp_agentic_500_jailbreaks*.json",
    "data/owasp_agentic_top10_jailbreaks*.json",
    "data/advanced_jailbreak_samples*.json",
    "data/agentic_scenarios_10_mixed.json",
    "data/agentic_scenarios_100*.json",
    "data/agentic_scenarios_20.json",
    "data/agentic_scenarios_5_safe.json",
    "data/agentic_scenarios_MIR_eval*.json",
    "data/agentic_scenarios_smoke*.json",
    "data/agentic_scenarios_top10.json",
    "data/smoke_jailbroken_*.json",
    "data/generate_*.py",
    # (data/agentic_scenarios_owasp_top10_50.json is kept — the only public dataset)
    # large binary assets
    "literature/**",
    "*.pdf",
    "**/*.pdf",
    "*.mp4",
    "**/*.mp4",
    "*.mp3",
    "**/*.mp3",
    "*.mov",
    "**/*.mov",
]


def main():
    parser = argparse.ArgumentParser(description="Deploy to private HF Space")
    parser.add_argument("--repo", required=True,
                        help="HF Space repo id, e.g. myorg/agentic-safety-eval")
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"),
                        help="HF write token (or set HF_TOKEN env var)")
    parser.add_argument("--no-create", action="store_true",
                        help="Skip repo creation (use if space already exists)")
    args = parser.parse_args()

    if not args.token:
        sys.exit("Error: HF write token required (--token or HF_TOKEN env var)")

    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("huggingface_hub not installed — run: pip install huggingface_hub")

    api = HfApi(token=args.token)

    # Create the Space if it does not exist yet
    if not args.no_create:
        print(f"Creating private Docker Space: {args.repo}")
        try:
            api.create_repo(
                repo_id=args.repo,
                repo_type="space",
                space_sdk="docker",
                private=True,
                exist_ok=True,
            )
            print(f"  Space ready at https://huggingface.co/spaces/{args.repo}")
        except Exception as exc:
            sys.exit(f"Failed to create Space: {exc}")

    # Upload the workspace folder
    print(f"Uploading workspace to {args.repo} …")
    print("  (this may take a few minutes on first push)")
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=args.repo,
        repo_type="space",
        ignore_patterns=IGNORE_PATTERNS,
        commit_message="Deploy agentic-safety-eval",
    )
    print(f"\nDone! Your Space is building at:")
    print(f"  https://huggingface.co/spaces/{args.repo}")
    print("\nSet any required secrets in the Space settings:")
    print("  GENAI_STUDIO_API_KEY   — Purdue GenAI RCAC")
    print("  OLLAMA_CLOUD_API_KEY   — ollama.com cloud (auto-routes to api.ollama.com)")
    print("  OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, WANDB_API_KEY, …")


if __name__ == "__main__":
    main()
