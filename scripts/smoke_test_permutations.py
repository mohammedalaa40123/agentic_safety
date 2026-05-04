#!/usr/bin/env python3
"""
Smoke test: 1 sample × all attack × defense permutations.

Attacks : pair, crescendo
Defenses: none, agentshield, stepshield, progent, contextguard, jbshield, gradient_cuff
Target  : deepseek-r1:14b

Submits jobs sequentially, polls to completion, then prints a results table.
"""
from __future__ import annotations

import json, os, sys, time
from typing import Any, Dict, List, Optional
import requests

BASE  = "https://mo-alaa-agentic-safety-eval.hf.space/api"
RCAC_KEY = "sk-7f60852bbc2a4997b8d6676071ce1cb9"
RCAC_URL = "https://genai.rcac.purdue.edu/api"
CREDS = [{"provider_id": "genai", "api_key": RCAC_KEY, "base_url": RCAC_URL}]

CRESCENDO_P    = {"max_turns": 10, "escalation_stages": 5,
                  "benign_warmup_turns": 2, "patience": 3, "context_window": 6}
PAIR_P         = {"n_iterations": 5}

ATTACKS = {
    "pair":      [{"name": "pair",      "enabled": True, "params": PAIR_P}],
    "crescendo": [{"name": "crescendo", "enabled": True, "params": CRESCENDO_P}],
}

DEFENSES = ["none", "agentshield", "stepshield", "progent",
            "contextguard", "jbshield", "gradient_cuff"]

TARGET  = "deepseek-r1:14b"
DATASET = "agentic_scenarios_owasp_top10_50.json"
SCOPE   = {"mode": "sample", "n": 1, "seed": 42}   # deterministic 1-sample


def wait_for_space(retries: int = 20, delay: int = 15) -> bool:
    for i in range(retries):
        try:
            r = requests.get(f"{BASE}/eval/jobs", timeout=10)
            if r.status_code == 200:
                print("Space is up.")
                return True
        except Exception:
            pass
        print(f"  Waiting for Space … ({i+1}/{retries})")
        time.sleep(delay)
    return False


def launch(payload: Dict[str, Any]) -> str:
    r = requests.post(f"{BASE}/eval/launch", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def poll(job_id: str, interval: int = 20) -> Dict[str, Any]:
    while True:
        time.sleep(interval)
        r = requests.get(f"{BASE}/eval/{job_id}", timeout=15)
        r.raise_for_status()
        s = r.json()
        if s["status"] in ("completed", "failed", "cancelled"):
            return s
        p = s.get("progress")
        if p:
            print(f"    [{p['current']}/{p['total']}] {p.get('label','')[:70]}")


def get_results(job_id: str) -> Optional[List[Dict]]:
    try:
        r = requests.get(f"{BASE}/eval/{job_id}/results", timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            return data.get("records", [])
    except Exception:
        pass
    return None


def analyze(records: List[Dict]) -> Dict:
    if not records:
        return {"n": 0, "mir": None, "tir": None, "qtj": None}
    n = len(records)
    jb  = [bool(r.get("attack_success", False)) for r in records]
    tc  = [int(r.get("tool_calls_total",   0))  for r in records]
    q   = [int(r.get("queries",            0))  for r in records]
    mir = sum(jb) / n
    tir = sum(tc) / n
    qtj_vals = [q[i] for i in range(n) if jb[i]]
    qtj = sum(qtj_vals) / len(qtj_vals) if qtj_vals else None
    return {"n": n, "mir": mir, "tir": tir, "qtj": qtj}


def main():
    print("=== Smoke Test: all attack × defense permutations (n=1) ===\n")

    if not wait_for_space():
        sys.exit("Space did not come up in time.")

    results_summary = []

    for atk_name, atk_cfg in ATTACKS.items():
        for defense in DEFENSES:
            label = f"{atk_name:10} + {defense:15}"
            payload = {
                "target_provider": "genai",
                "target_model":    TARGET,
                "attack_provider": "genai",
                "attack_model":    "llama3.3:70b",
                "judge_provider":  "genai",
                "judge_model":     "llama3.3:70b",
                "dataset":         DATASET,
                "dataset_scope":   SCOPE,
                "attacks":         atk_cfg,
                "defenses":        [] if defense == "none" else [defense],
                "calls_per_minute": 20,
                "credentials":     CREDS,
            }

            print(f"[SUBMIT] {label}")
            try:
                jid = launch(payload)
                print(f"  job_id={jid}")
                final = poll(jid)
                status = final["status"]
                print(f"  → {status}  ({final.get('duration_seconds', 0):.0f}s)")

                records = get_results(jid) if status == "completed" else []
                stats   = analyze(records or [])
                results_summary.append({
                    "attack":  atk_name,
                    "defense": defense,
                    "job_id":  jid,
                    "status":  status,
                    **stats,
                })
            except Exception as exc:
                print(f"  ERROR: {exc}")
                results_summary.append({
                    "attack": atk_name, "defense": defense,
                    "status": "error", "error": str(exc),
                })

    # ── Results table ──────────────────────────────────────────────
    os.makedirs("results", exist_ok=True)
    out = "results/smoke_test_permutations.json"
    with open(out, "w") as f:
        json.dump(results_summary, f, indent=2)
    print(f"\nRaw results saved → {out}\n")

    print("=" * 70)
    print(f"{'Attack':12} {'Defense':16} {'Status':10} {'n':>3} {'MIR':>7} {'TIR':>6} {'QTJ':>6}")
    print("-" * 70)
    for r in results_summary:
        mir = f"{r['mir']:.0%}" if r.get("mir") is not None else "—"
        tir = f"{r['tir']:.1f}" if r.get("tir") is not None else "—"
        qtj = f"{r['qtj']:.1f}" if r.get("qtj") is not None else "—"
        print(f"{r['attack']:12} {r['defense']:16} {r['status']:10} "
              f"{r.get('n',0):>3} {mir:>7} {tir:>6} {qtj:>6}")
    print("=" * 70)

    # Quick analysis
    completed = [r for r in results_summary if r["status"] == "completed"]
    failed    = [r for r in results_summary if r["status"] != "completed"]
    print(f"\nCompleted: {len(completed)}/{len(results_summary)}")
    if failed:
        print(f"Failed/Error combos:")
        for r in failed:
            print(f"  {r['attack']} + {r['defense']}: {r.get('error', r['status'])}")

    # Best/worst defense by MIR
    scored = [r for r in completed if r.get("mir") is not None]
    if scored:
        best  = min(scored, key=lambda x: x["mir"])
        worst = max(scored, key=lambda x: x["mir"])
        print(f"\nMost effective defense (lowest MIR): {best['defense']} ({best['attack']}) → {best['mir']:.0%}")
        print(f"Least effective defense (highest MIR): {worst['defense']} ({worst['attack']}) → {worst['mir']:.0%}")


if __name__ == "__main__":
    main()
