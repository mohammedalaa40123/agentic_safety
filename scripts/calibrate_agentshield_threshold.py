#!/usr/bin/env python3
"""Calibrate AgentShield prompt threshold on labeled JSON scenarios.

Usage:
  python scripts/calibrate_agentshield_threshold.py \
      --data data/agentic_scenarios_MIR_eval_v2.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from defenses.agentshield import AgentShieldDefense, AgentShieldPolicy


@dataclass
class ScoredExample:
    label: int
    score: float


def is_malicious(example: Dict) -> int:
    flag = example.get("is_malicious")
    if flag is not None:
        return int(bool(flag))
    category = str(example.get("category", "")).lower()
    return int(any(tok in category for tok in ["unsafe", "malicious", "jailbreak", "harm", "attack"]))


def load_examples(path: str) -> List[Dict]:
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    return data


def fbeta(precision: float, recall: float, beta: float = 2.0) -> float:
    if precision <= 0.0 and recall <= 0.0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * precision * recall / (b2 * precision + recall + 1e-12)


def evaluate_threshold(examples: List[ScoredExample], threshold: float) -> Dict[str, float]:
    tp = fp = tn = fn = 0
    for ex in examples:
        pred = 1 if ex.score >= threshold else 0
        if pred == 1 and ex.label == 1:
            tp += 1
        elif pred == 1 and ex.label == 0:
            fp += 1
        elif pred == 0 and ex.label == 0:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    acc = (tp + tn) / max(1, tp + fp + tn + fn)
    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": acc,
        "f2": fbeta(precision, recall, beta=2.0),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Labeled dataset JSON")
    ap.add_argument("--model-id", default="protectai/deberta-v3-base-prompt-injection-v2")
    ap.add_argument("--disable-classifier", action="store_true")
    ap.add_argument("--min-threshold", type=float, default=0.40)
    ap.add_argument("--max-threshold", type=float, default=0.90)
    ap.add_argument("--step", type=float, default=0.02)
    args = ap.parse_args()

    policy = AgentShieldPolicy(
        model_id=args.model_id,
        use_classifier=not args.disable_classifier,
    )
    shield = AgentShieldDefense(policy=policy)

    raw = load_examples(args.data)
    scored: List[ScoredExample] = []
    for ex in raw:
        prompt = str(ex.get("goal") or ex.get("prompt") or ex.get("user_goal") or "")
        if not prompt:
            continue
        result = shield.filter_prompt(prompt)
        scored.append(ScoredExample(label=is_malicious(ex), score=float(result.confidence)))

    if not scored:
        raise RuntimeError("No examples with usable prompt text were found.")

    t = args.min_threshold
    all_rows: List[Dict[str, float]] = []
    while t <= args.max_threshold + 1e-9:
        all_rows.append(evaluate_threshold(scored, round(t, 4)))
        t += args.step

    best = max(all_rows, key=lambda r: (r["f2"], r["recall"], r["precision"]))

    print(f"examples={len(scored)}")
    print("best_threshold_by_f2")
    print(
        f"  threshold={best['threshold']:.2f} "
        f"precision={best['precision']:.3f} recall={best['recall']:.3f} "
        f"specificity={best['specificity']:.3f} accuracy={best['accuracy']:.3f} f2={best['f2']:.3f}"
    )

    print("\nthreshold_sweep")
    for row in all_rows:
        print(
            f"  t={row['threshold']:.2f} p={row['precision']:.3f} r={row['recall']:.3f} "
            f"sp={row['specificity']:.3f} f2={row['f2']:.3f} "
            f"tp={int(row['tp'])} fp={int(row['fp'])} tn={int(row['tn'])} fn={int(row['fn'])}"
        )


if __name__ == "__main__":
    main()
