#!/usr/bin/env python3
"""
Sequential job submitter for ICLR 2026 revision.

Phase 3: Crescendo on 7 models missing Crescendo data
Phase 4: Defense baselines (6) + defense eval (24) = 30 jobs

Usage:
    python scripts/submit_jobs.py --phase 3
    python scripts/submit_jobs.py --phase 4
    python scripts/submit_jobs.py --phase 3 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://mo-alaa-agentic-safety-eval.hf.space/api"

RCAC_KEY = os.getenv("RCAC_KEY", "sk-7f60852bbc2a4997b8d6676071ce1cb9")
RCAC_URL = "https://genai.rcac.purdue.edu/api"

CREDENTIALS = [
    {"provider_id": "genai", "api_key": RCAC_KEY, "base_url": RCAC_URL}
]

CRESCENDO_PARAMS = {
    "max_turns": 10,
    "escalation_stages": 5,
    "benign_warmup_turns": 2,
    "patience": 3,
    "context_window": 6,
}

PAIR_PARAMS = {"n_iterations": 5}

DATASET_CTF50 = "agentic_scenarios_owasp_top10_50.json"


def _crescendo_attack():
    return [{"name": "crescendo", "enabled": True, "params": CRESCENDO_PARAMS}]


def _pair_attack():
    return [{"name": "pair", "enabled": True, "params": PAIR_PARAMS}]


def _job(target: str, attacks, defenses=None, label="") -> Dict[str, Any]:
    return {
        "target_provider": "genai",
        "target_model": target,
        "attack_provider": "genai",
        "attack_model": "llama3.3:70b",
        "judge_provider": "genai",
        "judge_model": "llama3.3:70b",
        "dataset": DATASET_CTF50,
        "dataset_scope": {"mode": "full"},
        "attacks": attacks,
        "defenses": defenses or [],
        "calls_per_minute": 20,
        "credentials": CREDENTIALS,
        "_label": label,
    }


# ── Phase 3: Crescendo on 7 models missing data ────────────────────────────

PHASE3_JOBS = [
    _job("deepseek-r1:7b",    _crescendo_attack(), label="P3-1 deepseek-r1:7b crescendo"),
    _job("llama3.1:latest",   _crescendo_attack(), label="P3-2 llama3.1 crescendo"),
    _job("llama3.2:latest",   _crescendo_attack(), label="P3-3 llama3.2 crescendo"),
    _job("llama3.3:70b",      _crescendo_attack(), label="P3-4 llama3.3:70b crescendo"),
    _job("qwen3:1.7b",        _crescendo_attack(), label="P3-5 qwen3:1.7b crescendo"),
    _job("qwen3:14b",         _crescendo_attack(), label="P3-6 qwen3:14b crescendo"),
    _job("qwen3:30b",         _crescendo_attack(), label="P3-7 qwen3:30b crescendo"),
]

# ── Phase 4: Defense baselines + 24 defense cells ─────────────────────────

_DEFENSE_MODELS = ["deepseek-r1:14b", "llama3.3:70b", "qwen3:14b"]
_DEFENSES = ["agentshield", "stepshield", "progent", "contextguard"]

PHASE4_JOBS = []

# 6 no-defense baselines (PAIR + Crescendo × 3 models)
for m in _DEFENSE_MODELS:
    PHASE4_JOBS.append(_job(m, _pair_attack(),      label=f"P4-baseline {m} pair"))
    PHASE4_JOBS.append(_job(m, _crescendo_attack(), label=f"P4-baseline {m} crescendo"))

# 24 defense cells
for d in _DEFENSES:
    for m in _DEFENSE_MODELS:
        PHASE4_JOBS.append(_job(m, _pair_attack(),      defenses=[d], label=f"P4 {d} {m} pair"))
        PHASE4_JOBS.append(_job(m, _crescendo_attack(), defenses=[d], label=f"P4 {d} {m} crescendo"))


# ── Submission helpers ─────────────────────────────────────────────────────

def launch_job(payload: Dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if not k.startswith("_")}
    resp = requests.post(f"{BASE_URL}/eval/launch", json=clean, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def wait_for_job(job_id: str, poll_interval: int = 30) -> Dict[str, Any]:
    while True:
        time.sleep(poll_interval)
        r = requests.get(f"{BASE_URL}/eval/{job_id}", timeout=15)
        r.raise_for_status()
        status = r.json()
        s = status["status"]
        p = status.get("progress")
        if p:
            print(f"    [{p['current']}/{p['total']}] {p.get('label','')[:80]}")
        else:
            print(f"    status={s}")
        if s in ("completed", "failed", "cancelled"):
            return status


def run_phase(jobs: list, phase_name: str, dry_run: bool = False, start_from: int = 0):
    summary_path = f"results/phase_{phase_name}_summary.json"
    summary = []

    for i, job in enumerate(jobs):
        if i < start_from:
            print(f"[{i+1}/{len(jobs)}] Skipping (start_from={start_from}): {job['_label']}")
            continue

        label = job["_label"]
        print(f"\n[{i+1}/{len(jobs)}] {label}")

        if dry_run:
            print("  DRY RUN — skipping submission")
            continue

        try:
            job_id = launch_job(job)
            print(f"  Launched → job_id={job_id}")
            final = wait_for_job(job_id)

            entry = {
                "index": i,
                "label": label,
                "job_id": job_id,
                "status": final["status"],
                "duration_seconds": final.get("duration_seconds"),
                "result_path": final.get("result_path"),
                "error": final.get("error"),
            }
            summary.append(entry)
            print(f"  Done → status={final['status']}  duration={final.get('duration_seconds',0):.0f}s")

            if final["status"] == "failed":
                print(f"  ERROR: {final.get('error')}")
                print(f"  Last logs: {final.get('log_tail', [])[-5:]}")

        except Exception as exc:
            print(f"  EXCEPTION: {exc}")
            summary.append({"index": i, "label": label, "error": str(exc)})

        # Save progress after each job
        os.makedirs("results", exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

    print(f"\nPhase {phase_name} complete. Summary saved to {summary_path}")
    ok = sum(1 for e in summary if e.get("status") == "completed")
    fail = sum(1 for e in summary if e.get("status") == "failed")
    print(f"  Completed: {ok}/{len(jobs)}   Failed: {fail}/{len(jobs)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=[3, 4], required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start-from", type=int, default=0,
                    help="Skip first N jobs (resume from crash)")
    args = ap.parse_args()

    if args.phase == 3:
        run_phase(PHASE3_JOBS, "3", dry_run=args.dry_run, start_from=args.start_from)
    elif args.phase == 4:
        run_phase(PHASE4_JOBS, "4", dry_run=args.dry_run, start_from=args.start_from)


if __name__ == "__main__":
    main()
