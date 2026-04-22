#!/usr/bin/env python3
"""
Smoke test matrix launcher.

Group A – All attacks, no defenses, for every leaderboard model.
Group B – All defenses on deepseek-r1:14b (fastest mid-tier target).

Each job: n=5 scenarios, seed=77 (different from existing seed=42 runs).
"""
import json
import time
import sys
import urllib.request
import urllib.error

API = "http://localhost:7861/api/eval"
API_KEY = "sk-6d974b477afc48c88de95978d2f662ef"
ATTACKER = "genai:llama3.3:70b"
JUDGE    = "genai:llama3.3:70b"

CREDENTIALS = [{"provider_id": "genai", "api_key": API_KEY}]
DATASET = "owasp_agentic_500_jailbreaks_v2.json"
SCOPE   = {"mode": "sample", "n": 5, "seed": 77}

# ── All 9 leaderboard models ───────────────────────────────────────────────────
ALL_MODELS = [
    "genai:deepseek-r1:70b",
    "genai:llama3.3:70b",
    "genai:deepseek-r1:14b",
    "genai:deepseek-r1:7b",
    "genai:llama3.1:latest",
    "genai:llama3.2:latest",
    "genai:qwen3:1.7b",
    "genai:qwen3:14b",
    "genai:qwen3:30b",
]

# Representative target for defense sweeps (mid-tier, fastest to respond)
DEFENSE_TARGET = "genai:deepseek-r1:14b"

# ── Attack groups ──────────────────────────────────────────────────────────────
ALL_ATTACKS  = ["pair", "crescendo", "baseline", "gcg", "prompt_fusion"]
BASE_ATTACKS = ["pair", "crescendo", "baseline"]   # used for defense combos

ALL_DEFENSES = ["agentshield", "progent", "stepshield", "contextguard", "jbshield"]


def post(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API}/launch",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def build_payload(target: str, attacks: list, defenses: list) -> dict:
    return {
        "target_provider": "genai",
        "target_model": target.split(":", 1)[1],   # strip "genai:" prefix
        "attack_provider": "genai",
        "attack_model": ATTACKER.split(":", 1)[1],
        "judge_provider": "genai",
        "judge_model": JUDGE.split(":", 1)[1],
        "dataset": DATASET,
        "dataset_scope": SCOPE,
        "attacks": attacks,
        "defenses": defenses,
        "calls_per_minute": 20,
        "credentials": CREDENTIALS,
    }


def launch_all():
    jobs = []

    # ── Group A: all attacks, no defenses, every model ────────────────────────
    print("=== Group A: All attacks × All models ===")
    for model in ALL_MODELS:
        label = f"{model} | attacks={ALL_ATTACKS} | defenses=none"
        try:
            resp = post(build_payload(model, ALL_ATTACKS, []))
            jid = resp.get("id", "?")
            st  = resp.get("status", "?")
            err = resp.get("error")
            if err:
                print(f"  FAIL  {label}\n        err: {err}")
            else:
                print(f"  OK    {jid[:8]}  {label}")
                jobs.append({"id": jid, "label": label})
        except Exception as e:
            print(f"  ERR   {label}\n        {e}")
        time.sleep(0.4)   # small gap to avoid hammering the server

    # ── Group B: each defense, base attacks, fixed target ─────────────────────
    print(f"\n=== Group B: Defenses × {DEFENSE_TARGET} ===")
    for defense in ALL_DEFENSES:
        label = f"{DEFENSE_TARGET} | attacks={BASE_ATTACKS} | defense={defense}"
        try:
            resp = post(build_payload(DEFENSE_TARGET, BASE_ATTACKS, [defense]))
            jid = resp.get("id", "?")
            st  = resp.get("status", "?")
            err = resp.get("error")
            if err:
                print(f"  FAIL  {label}\n        err: {err}")
            else:
                print(f"  OK    {jid[:8]}  {label}")
                jobs.append({"id": jid, "label": label})
        except Exception as e:
            print(f"  ERR   {label}\n        {e}")
        time.sleep(0.4)

    print(f"\nLaunched {len(jobs)} jobs total.")
    print("\n--- Job IDs ---")
    for j in jobs:
        print(f"  {j['id']}  {j['label']}")

    # Save for monitoring
    with open("/tmp/smoke_matrix_jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)
    print("\nSaved to /tmp/smoke_matrix_jobs.json")
    return jobs


if __name__ == "__main__":
    launch_all()
