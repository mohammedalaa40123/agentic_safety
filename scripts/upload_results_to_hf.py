#!/usr/bin/env python3
"""
upload_results_to_hf.py — Push all local result JSON files to the
Hugging Face dataset so the Space leaderboard shows all experiments.

Usage:
    export HF_TOKEN="hf_..."
    python scripts/upload_results_to_hf.py

Options:
    --repo    HF dataset repo (default: Mo-alaa/agentic-safety-results)
    --dir     Local results dir (default: results/agentic_experiments_v2_500)
    --dry-run Print files that would be uploaded without uploading
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload results to HF dataset")
    parser.add_argument("--repo",    default="Mo-alaa/agentic-safety-results",
                        help="HF dataset repo ID")
    parser.add_argument("--dir",     default="results/agentic_experiments_v2_500",
                        help="Local results directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print files without uploading")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("ERROR: Set HF_TOKEN environment variable first.")
        print("  export HF_TOKEN='hf_...'")
        sys.exit(1)

    results_dir = Path(args.dir).resolve()
    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        sys.exit(1)

    json_files = sorted(results_dir.rglob("*.json"))
    if not json_files:
        print("No JSON result files found.")
        sys.exit(0)

    print(f"\n📦  Preparing to upload {len(json_files)} result files")
    print(f"    From : {results_dir}")
    print(f"    To   : hf://datasets/{args.repo}/results/")
    print()

    if args.dry_run:
        for f in json_files:
            rel = f.relative_to(results_dir)
            print(f"  [DRY-RUN] would upload → results/{rel}")
        print(f"\n✓  Dry-run complete — {len(json_files)} files listed.")
        return

    api = HfApi(token=token)

    # Ensure dataset repo exists (create if not)
    try:
        api.repo_info(repo_id=args.repo, repo_type="dataset", token=token)
        print(f"✓  Dataset repo found: {args.repo}")
    except Exception:
        print(f"  Creating dataset repo: {args.repo} …")
        api.create_repo(repo_id=args.repo, repo_type="dataset", private=True, token=token)
        print(f"✓  Created: {args.repo}")

    uploaded = 0
    failed   = 0

    for fpath in json_files:
        rel = fpath.relative_to(results_dir)
        path_in_repo = f"results/{rel}"
        try:
            api.upload_file(
                path_or_fileobj=str(fpath),
                path_in_repo=path_in_repo,
                repo_id=args.repo,
                repo_type="dataset",
                token=token,
                commit_message=f"Add {rel.parts[0]}",
            )
            print(f"  ✓  {path_in_repo}")
            uploaded += 1
        except Exception as exc:
            print(f"  ✗  {path_in_repo}  — {exc}")
            failed += 1

    print(f"\n{'✅' if failed == 0 else '⚠️ '}  Done: {uploaded} uploaded, {failed} failed.")
    print(f"\nThe Space will now auto-sync from:\n  https://huggingface.co/datasets/{args.repo}")
    print(f"Leaderboard at:\n  https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval#leaderboard")


if __name__ == "__main__":
    main()
