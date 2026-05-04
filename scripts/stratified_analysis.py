#!/usr/bin/env python3
"""
Stratified Analysis — addresses ICLR reviewer W7 and Q5.

Disaggregates results by:
  1. Dataset type: 500-OWASP synthetic goals vs. 50 CTF-like scenarios
  2. OWASP category: Per-category MIR, TIR, QTJ breakdown
  3. Tool type: Per-tool engagement and success rates

Produces LaTeX tables and summary statistics for the paper.

Usage:
  python scripts/stratified_analysis.py \
    --results-dir results/agentic_experiments_v2_500 \
    --dataset-500 data/owasp_agentic_500_jailbreaks_v2.json \
    --dataset-50 data/agentic_scenarios_owasp_top10_50.json \
    --output-dir report/stratified
"""

from __future__ import annotations

import argparse
import csv
import json
import glob
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics.statistical_utils import wilson_ci, format_ci_latex, format_with_n


def load_dataset_goals(path: str) -> Dict[str, Dict[str, Any]]:
    """Load dataset and create a lookup by goal text."""
    with open(path) as f:
        data = json.load(f)

    lookup = {}
    for entry in data:
        goal = entry.get("user_goal", entry.get("goal", ""))
        lookup[goal] = entry
    return lookup


def load_all_records(results_dir: str) -> List[Dict[str, Any]]:
    """Load all experiment records from the results directory."""
    records = []
    for jf in sorted(glob.glob(os.path.join(results_dir, "**", "results_*.json"), recursive=True)):
        try:
            with open(jf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if isinstance(data, list):
            records.extend(data)
        elif isinstance(data, dict):
            records.extend(data.get("records", []))

    return records


def categorize_by_owasp(
    records: List[Dict[str, Any]],
    dataset_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group records by their OWASP category."""
    by_category = defaultdict(list)
    for rec in records:
        goal = rec.get("goal", rec.get("user_goal", ""))
        dataset_entry = dataset_lookup.get(goal, {})
        category = dataset_entry.get("category", rec.get("category", "unknown"))
        # Normalize category names
        owasp_id = dataset_entry.get("owasp_id", "")
        owasp_name = dataset_entry.get("owasp_name", category)
        rec["_owasp_id"] = owasp_id
        rec["_owasp_name"] = owasp_name
        rec["_expected_tools"] = dataset_entry.get("expected_tools", [])
        rec["_is_malicious"] = dataset_entry.get("is_malicious", True)
        by_category[owasp_name or category].append(rec)
    return dict(by_category)


def compute_category_metrics(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute MIR, TIR, QTJ for a group of records."""
    n = len(records)
    if n == 0:
        return {"n": 0, "MIR": 0.0, "MIR_ci": (0.0, 0.0), "TIR": 0.0, "QTJ_mean": 0.0}

    successes = sum(1 for r in records if r.get("attack_success"))
    mir = successes / n
    mir_ci = wilson_ci(successes, n)

    # TIR
    total_tool_calls = sum(r.get("tool_calls_total", 0) for r in records)
    harmful_tool_calls = sum(r.get("tool_calls_harmful", 0) for r in records)
    tir = harmful_tool_calls / total_tool_calls if total_tool_calls > 0 else 0.0

    # QTJ (only over successes)
    qtj_values = [
        r.get("queries", 0) for r in records if r.get("attack_success")
    ]
    qtj_mean = sum(qtj_values) / len(qtj_values) if qtj_values else float("inf")

    # Tool engagement (L2)
    tool_engaged = 0
    for r in records:
        expected = set(r.get("_expected_tools", []))
        if not expected:
            continue
        # Check if any expected tool was invoked
        stages = r.get("stages", r.get("steps", []))
        if isinstance(stages, str):
            try:
                stages = json.loads(stages)
            except json.JSONDecodeError:
                stages = []
        invoked = set()
        if isinstance(stages, list):
            for s in stages:
                if isinstance(s, dict):
                    tool_name = s.get("action") or s.get("tool", "")
                    if tool_name:
                        invoked.add(tool_name)
                    target = s.get("target", {})
                    if isinstance(target, dict):
                        for tc in target.get("tool_calls", []):
                            invoked.add(tc.get("tool", tc.get("name", "")))
        if invoked & expected:
            tool_engaged += 1

    te_rate = tool_engaged / n if n > 0 else 0.0

    return {
        "n": n,
        "MIR": mir,
        "MIR_ci": mir_ci,
        "TIR": tir,
        "QTJ_mean": qtj_mean,
        "TE_rate": te_rate,
        "successes": successes,
        "total_tool_calls": total_tool_calls,
        "harmful_tool_calls": harmful_tool_calls,
    }


def generate_category_latex_table(
    category_metrics: Dict[str, Dict[str, Any]],
    caption: str = "Per-Category Metrics",
    label: str = "tab:category_metrics",
) -> str:
    """Generate a LaTeX table of per-category metrics."""
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\small",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\begin{tabular}{lrcccc}",
        r"\toprule",
        r"Category & $n$ & MIR [95\% CI] & TE & TIR & QTJ \\",
        r"\midrule",
    ]

    for cat, metrics in sorted(category_metrics.items()):
        n = metrics["n"]
        mir_str = format_ci_latex(metrics["MIR"], metrics["MIR_ci"])
        te_str = f"{metrics['TE_rate']:.1%}"
        tir_str = f"{metrics['TIR']:.1%}"
        qtj_str = f"{metrics['QTJ_mean']:.1f}" if metrics["QTJ_mean"] < 1e6 else "—"
        # Truncate category name for table width
        cat_short = cat[:35] + "…" if len(cat) > 35 else cat
        lines.append(
            rf"  {cat_short} & {n} & {mir_str} & {te_str} & {tir_str} & {qtj_str} \\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_cross_dataset_comparison(
    metrics_500: Dict[str, Any],
    metrics_50: Dict[str, Any],
) -> str:
    """Generate a LaTeX table comparing 500-OWASP vs 50-CTF datasets."""
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\caption{Cross-Dataset Comparison: 500-OWASP Synthetic vs. 50-CTF Structured Scenarios}",
        r"\label{tab:cross_dataset}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Metric & 500-OWASP Synthetic & 50-CTF Structured \\",
        r"\midrule",
    ]

    for key, label in [
        ("n", "Sample Size"),
        ("MIR", "MIR"),
        ("TE_rate", "Tool Engagement"),
        ("TIR", "TIR"),
        ("QTJ_mean", "Mean QTJ"),
    ]:
        v500 = metrics_500.get(key, 0)
        v50 = metrics_50.get(key, 0)

        if key == "n":
            lines.append(rf"  {label} & {v500} & {v50} \\")
        elif key == "MIR":
            ci500 = format_ci_latex(v500, metrics_500.get("MIR_ci", (0, 0)))
            ci50 = format_ci_latex(v50, metrics_50.get("MIR_ci", (0, 0)))
            lines.append(rf"  {label} & {ci500} & {ci50} \\")
        elif key == "QTJ_mean":
            q500 = f"{v500:.1f}" if v500 < 1e6 else "—"
            q50 = f"{v50:.1f}" if v50 < 1e6 else "—"
            lines.append(rf"  {label} & {q500} & {q50} \\")
        else:
            lines.append(rf"  {label} & {v500:.1%} & {v50:.1%} \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Stratified analysis of results")
    parser.add_argument("--results-dir", type=str,
                        default="results/agentic_experiments_v2_500")
    parser.add_argument("--dataset-500", type=str,
                        default="data/owasp_agentic_500_jailbreaks_v2.json")
    parser.add_argument("--dataset-50", type=str,
                        default="data/agentic_scenarios_owasp_top10_50.json")
    parser.add_argument("--output-dir", type=str, default="report/stratified")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load datasets
    print("Loading datasets...")
    goals_500 = load_dataset_goals(args.dataset_500)
    goals_50 = load_dataset_goals(args.dataset_50)
    goals_500_set = set(goals_500.keys())
    goals_50_set = set(goals_50.keys())

    # Load all records
    print("Loading experiment records...")
    all_records = load_all_records(args.results_dir)
    print(f"  Loaded {len(all_records)} total records")

    # Split records by dataset source
    records_500 = [r for r in all_records if r.get("goal", r.get("user_goal", "")) in goals_500_set]
    records_50 = [r for r in all_records if r.get("goal", r.get("user_goal", "")) in goals_50_set]
    records_unknown = [
        r for r in all_records
        if r.get("goal", r.get("user_goal", "")) not in goals_500_set
        and r.get("goal", r.get("user_goal", "")) not in goals_50_set
    ]

    print(f"  500-OWASP records: {len(records_500)}")
    print(f"  50-CTF records: {len(records_50)}")
    print(f"  Unmatched records: {len(records_unknown)}")

    # Aggregate metrics per dataset
    metrics_500 = compute_category_metrics(records_500)
    metrics_50 = compute_category_metrics(records_50)

    print(f"\n500-OWASP: MIR={metrics_500['MIR']:.1%} (n={metrics_500['n']})")
    print(f"50-CTF:    MIR={metrics_50['MIR']:.1%} (n={metrics_50['n']})")

    # Per-category breakdown (50-CTF only, since it has structured OWASP IDs)
    print("\n--- Per-OWASP-Category Breakdown (50-CTF) ---")
    cat_50 = categorize_by_owasp(records_50, goals_50)
    cat_metrics_50 = {}
    for cat, recs in sorted(cat_50.items()):
        m = compute_category_metrics(recs)
        cat_metrics_50[cat] = m
        print(f"  {cat}: MIR={m['MIR']:.1%} (n={m['n']})")

    # Per-category breakdown (500-OWASP)
    print("\n--- Per-Category Breakdown (500-OWASP) ---")
    cat_500 = categorize_by_owasp(records_500, goals_500)
    cat_metrics_500 = {}
    for cat, recs in sorted(cat_500.items()):
        m = compute_category_metrics(recs)
        cat_metrics_500[cat] = m
        print(f"  {cat}: MIR={m['MIR']:.1%} (n={m['n']})")

    # Generate LaTeX tables
    cross_table = generate_cross_dataset_comparison(metrics_500, metrics_50)
    with open(os.path.join(args.output_dir, "cross_dataset.tex"), "w") as f:
        f.write(cross_table)
    print(f"\nWrote cross-dataset table to {args.output_dir}/cross_dataset.tex")

    cat_table_50 = generate_category_latex_table(
        cat_metrics_50,
        caption="Per-OWASP-Category Metrics (50 CTF-like Scenarios)",
        label="tab:ctf_category",
    )
    with open(os.path.join(args.output_dir, "ctf_category.tex"), "w") as f:
        f.write(cat_table_50)

    cat_table_500 = generate_category_latex_table(
        cat_metrics_500,
        caption="Per-Category Metrics (500 OWASP-Aligned Synthetic Goals)",
        label="tab:owasp_category",
    )
    with open(os.path.join(args.output_dir, "owasp_category.tex"), "w") as f:
        f.write(cat_table_500)

    # Save summary JSON
    summary = {
        "dataset_500": metrics_500,
        "dataset_50": metrics_50,
        "per_category_500": cat_metrics_500,
        "per_category_50": cat_metrics_50,
    }
    with open(os.path.join(args.output_dir, "stratified_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Wrote summary to {args.output_dir}/stratified_summary.json")


if __name__ == "__main__":
    main()
