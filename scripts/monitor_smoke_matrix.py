#!/usr/bin/env python3
"""
Poll /tmp/smoke_matrix_jobs.json and print a live status table.
Run: python scripts/monitor_smoke_matrix.py
"""
import json
import time
import urllib.request
import sys

API = "http://localhost:7861/api/eval"
JOBS_FILE = "/tmp/smoke_matrix_jobs.json"

STATUS_SYMBOL = {
    "queued":    "⏳",
    "running":   "🔄",
    "completed": "✅",
    "failed":    "❌",
    "error":     "💥",
}


def fetch(job_id: str) -> dict:
    try:
        with urllib.request.urlopen(f"{API}/{job_id}", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"status": "error", "error": str(e)}


def summarise(job: dict) -> str:
    rp = job.get("result_path") or ""
    if rp:
        # Try to get quick ASR from result file
        try:
            with open(rp) as f:
                data = json.load(f)
            if isinstance(data, dict) and "summary" in data:
                s = data["summary"]
                return f"N={s['total_experiments']} ASR={s['ASR']:.0%} Task={s.get('Task_Success',0):.0%}"
            elif isinstance(data, list):
                import statistics
                asr = statistics.mean(
                    1 if str(r.get("attack_success", "")).lower() in ("true", "1") else 0
                    for r in data if isinstance(r, dict)
                )
                return f"N={len(data)} ASR={asr:.0%}"
        except Exception:
            pass
    tail = job.get("log_tail") or []
    return tail[-1].strip() if tail else ""


def run_once(jobs: list) -> tuple[int, int]:
    done = 0
    total = len(jobs)
    rows = []
    for j in jobs:
        info = fetch(j["id"])
        st = info.get("status", "?")
        sym = STATUS_SYMBOL.get(st, "?")
        detail = summarise(info) if st == "completed" else (info.get("error") or "")
        rows.append((sym, st, j["id"][:8], j["label"], detail))
        if st in ("completed", "failed", "error"):
            done += 1

    # Print table
    print(f"\n{'─'*90}")
    print(f"  {'SYM'} {'STATUS':10s} {'ID':8s}  {'LABEL':60s}  {'DETAIL'}")
    print(f"{'─'*90}")
    for sym, st, jid, label, detail in rows:
        label_short = label[:58]
        print(f"  {sym}  {st:10s}  {jid}  {label_short:58s}  {detail}")
    print(f"{'─'*90}")
    print(f"  {done}/{total} done")
    return done, total


def main():
    with open(JOBS_FILE) as f:
        jobs = json.load(f)

    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"Monitoring {len(jobs)} jobs — polling every {interval}s. Ctrl-C to stop.\n")

    while True:
        done, total = run_once(jobs)
        if done == total:
            print("\nAll jobs finished!")
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
