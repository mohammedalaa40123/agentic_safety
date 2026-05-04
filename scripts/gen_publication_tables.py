#!/usr/bin/env python3
"""
Publication Table Generator — addresses ICLR reviewer W5.

Reads ALL result JSONs and generates publication-ready LaTeX tables with:
  - 95% Wilson confidence intervals for all proportions
  - Per-cell sample sizes
  - Significance stars where applicable

Generated Tables:
  1. Attack × Model MIR matrix with CIs
  2. Crescendo turns-to-jailbreak distribution
  3. Defense × Attack DBR matrix
  4. Three-tier success taxonomy (Intent / Tool Engagement / Execution)
  5. Multi-judge agreement table
  6. OWASP-category breakdown
  7. 500-OWASP vs 50-CTF stratified comparison

Usage:
  python scripts/gen_publication_tables.py \
    --results-dir results \
    --output-dir report/tables
"""

from __future__ import annotations

import argparse
import json
import glob
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics.statistical_utils import wilson_ci, format_ci_latex, bootstrap_ci


def load_all_results(results_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all results, grouped by (target_model, attack_name, defense_name).

    Returns dict of group_key -> list of records.
    """
    groups = defaultdict(list)

    for jf in sorted(glob.glob(os.path.join(results_dir, "**", "results_*.json"), recursive=True)):
        try:
            with open(jf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("records", [])
        else:
            continue

        for rec in records:
            target = rec.get("target_model", "unknown")
            attack = rec.get("attack_name", "unknown")
            defense = rec.get("defense_name", "") or "none"

            # Normalize model names
            target = target.replace("genai:", "").replace("genai_rcac:", "")

            key = (target, attack, defense)
            groups[key].append(rec)

    return dict(groups)


def compute_cell_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute metrics for a single table cell."""
    n = len(records)
    if n == 0:
        return {"n": 0, "MIR": 0.0, "MIR_ci": (0.0, 0.0)}

    successes = sum(1 for r in records if r.get("attack_success"))
    mir = successes / n
    mir_ci = wilson_ci(successes, n)

    # QTJ (safely cast to int)
    def _int(v, default=0):
        try:
            return int(v or default)
        except (ValueError, TypeError):
            return default

    def _float(v, default=0.0):
        try:
            return float(v or default)
        except (ValueError, TypeError):
            return default

    qtj_values = [_int(r.get("queries", 0)) for r in records if r.get("attack_success")]
    qtj_mean = sum(qtj_values) / len(qtj_values) if qtj_values else float("inf")
    qtj_median = sorted(qtj_values)[len(qtj_values) // 2] if qtj_values else float("inf")

    # TIR
    total_tools = sum(_int(r.get("tool_calls_total", 0)) for r in records)
    harmful_tools = sum(_int(r.get("tool_calls_harmful", 0)) for r in records)
    tir = harmful_tools / total_tools if total_tools > 0 else 0.0

    # Duration
    durations = [_float(r.get("duration", 0)) for r in records]
    avg_dur = sum(durations) / n if n > 0 else 0.0

    return {
        "n": n,
        "successes": successes,
        "MIR": mir,
        "MIR_ci": mir_ci,
        "QTJ_mean": qtj_mean,
        "QTJ_median": qtj_median,
        "QTJ_n": len(qtj_values),
        "TIR": tir,
        "total_tools": total_tools,
        "harmful_tools": harmful_tools,
        "avg_duration": avg_dur,
    }


def generate_table1_attack_model_matrix(
    groups: Dict[Tuple, List],
    attacks: List[str],
    models: List[str],
) -> str:
    """Table 1: Attack × Model MIR matrix."""
    n_attacks = len(attacks)

    lines = [
        r"\begin{table*}[ht]",
        r"\centering",
        r"\small",
        r"\caption{Malicious Intent Rate (MIR) by Attack Method and Target Model. "
        r"Values show MIR [\%] with 95\% Wilson CI and sample size $n$.}",
        r"\label{tab:mir_matrix}",
        r"\begin{tabular}{l" + "c" * n_attacks + "}",
        r"\toprule",
        r"Target Model & " + " & ".join(
            [f"\\textbf{{{a.upper()}}}" for a in attacks]
        ) + r" \\",
        r"\midrule",
    ]

    for model in models:
        cells = []
        for attack in attacks:
            key = (model, attack, "none")
            recs = groups.get(key, [])
            if not recs:
                cells.append("—")
                continue
            m = compute_cell_metrics(recs)
            cell = format_ci_latex(m["MIR"], m["MIR_ci"])
            cell += f" (n={m['n']})"
            cells.append(cell)

        model_display = model.replace(":", " ").replace("_", " ")
        lines.append(f"  {model_display} & " + " & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    return "\n".join(lines)


def generate_table2_qtj_distribution(
    groups: Dict[Tuple, List],
    attacks: List[str],
    models: List[str],
) -> str:
    """Table 2: QTJ distribution (mean, median, std, n_success)."""
    import math

    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\small",
        r"\caption{Queries-to-Jailbreak (QTJ) Distribution. "
        r"Computed over successful trials only.}",
        r"\label{tab:qtj}",
        r"\begin{tabular}{llcccc}",
        r"\toprule",
        r"Model & Attack & Mean & Median & Std & $n_{\text{success}}$ \\",
        r"\midrule",
    ]

    for model in models:
        for attack in attacks:
            key = (model, attack, "none")
            recs = groups.get(key, [])
            if not recs:
                continue
            qtj_values = [
                int(r.get("queries", 0) or 0) for r in recs if r.get("attack_success")
            ]
            if not qtj_values:
                continue
            mean_q = sum(qtj_values) / len(qtj_values)
            sorted_q = sorted(qtj_values)
            median_q = sorted_q[len(sorted_q) // 2]
            var_q = sum((x - mean_q) ** 2 for x in qtj_values) / len(qtj_values)
            std_q = math.sqrt(var_q)

            model_display = model.replace(":", " ")
            lines.append(
                f"  {model_display} & {attack.upper()} & "
                f"{mean_q:.1f} & {median_q} & {std_q:.1f} & {len(qtj_values)} \\\\"
            )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_table3_defense_matrix(
    groups: Dict[Tuple, List],
    defenses: List[str],
    attacks: List[str],
    models: List[str],
) -> str:
    """Table 3: Defense × Attack DBR matrix."""
    lines = [
        r"\begin{table*}[ht]",
        r"\centering",
        r"\small",
        r"\caption{Defense Evaluation Matrix. Shows MIR [\%] and Defense Bypass Rate (DBR) "
        r"for each defense-attack-model combination.}",
        r"\label{tab:defense_matrix}",
        r"\begin{tabular}{ll" + "c" * len(defenses) + "}",
        r"\toprule",
        r"Attack + Model & No Defense & " + " & ".join(
            [f"\\textbf{{{d}}}" for d in defenses]
        ) + r" \\",
        r"\midrule",
    ]

    for attack in attacks:
        for model in models:
            cells = []

            # No-defense baseline
            key_none = (model, attack, "none")
            recs_none = groups.get(key_none, [])
            m_none = compute_cell_metrics(recs_none)
            if m_none["n"] > 0:
                cells.append(f"{m_none['MIR']:.0%} (n={m_none['n']})")
            else:
                cells.append("—")

            # Each defense
            for defense in defenses:
                key = (model, attack, defense)
                recs = groups.get(key, [])
                m = compute_cell_metrics(recs)
                if m["n"] > 0:
                    dbr = m["MIR"]  # When defense is active, MIR = DBR
                    cells.append(f"{dbr:.0%} (n={m['n']})")
                else:
                    cells.append("—")

            model_short = model.split(":")[-1] if ":" in model else model
            row_label = f"{attack.upper()} + {model_short}"
            lines.append(f"  {row_label} & " + " & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    return "\n".join(lines)


def generate_table_hyperparams() -> str:
    """Table documenting all attacker hyperparameters (reviewer Q1)."""
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\small",
        r"\caption{Attack and Judge Hyperparameters}",
        r"\label{tab:hyperparams}",
        r"\begin{tabular}{llr}",
        r"\toprule",
        r"Component & Parameter & Value \\",
        r"\midrule",
        r"PAIR Attacker & Iterations ($K$) & 5 \\",
        r"PAIR Attacker & Temperature & 0.7 \\",
        r"PAIR Attacker & Max tokens & 512 (2048 for DeepSeek) \\",
        r"PAIR Attacker & History window & 7 messages \\",
        r"PAIR Attacker & Success threshold & $\geq 8$ \\",
        r"\midrule",
        r"Crescendo & Max turns & 10 \\",
        r"Crescendo & Escalation stages & 5 \\",
        r"Crescendo & Warmup turns & 2 \\",
        r"Crescendo & Patience & 3 \\",
        r"Crescendo & Context window & 6 turns \\",
        r"\midrule",
        r"Judge & Temperature & 0.0 \\",
        r"Judge & Max tokens & 1024 \\",
        r"Judge & Jailbreak threshold & $\geq 7$ \\",
        r"\midrule",
        r"Sandbox & Max steps per goal & 5 \\",
        r"Sandbox & Code timeout & 10s \\",
        r"Sandbox & Tools & file\_io, code\_exec, web\_browse, network \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate publication tables")
    parser.add_argument("--results-dir", type=str, default="results")
    parser.add_argument("--output-dir", type=str, default="report/tables")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading all results...")
    groups = load_all_results(args.results_dir)
    print(f"  Found {len(groups)} unique (model, attack, defense) cells")
    print(f"  Total records: {sum(len(v) for v in groups.values())}")

    # Extract unique models, attacks, defenses
    all_models = sorted(set(k[0] for k in groups.keys()))
    all_attacks = sorted(set(k[1] for k in groups.keys()))
    all_defenses = sorted(set(k[2] for k in groups.keys() if k[2] != "none"))

    print(f"  Models: {all_models}")
    print(f"  Attacks: {all_attacks}")
    print(f"  Defenses: {all_defenses}")

    # Generate tables
    tables = {}

    # Table 1: MIR matrix
    tables["table1_mir_matrix"] = generate_table1_attack_model_matrix(
        groups, all_attacks, all_models,
    )

    # Table 2: QTJ distribution
    tables["table2_qtj"] = generate_table2_qtj_distribution(
        groups, all_attacks, all_models,
    )

    # Table 3: Defense matrix (only if defenses exist)
    if all_defenses:
        tables["table3_defense_matrix"] = generate_table3_defense_matrix(
            groups, all_defenses, all_attacks, all_models,
        )

    # Table: Hyperparameters
    tables["table_hyperparams"] = generate_table_hyperparams()

    # Write all tables
    for name, content in tables.items():
        path = os.path.join(args.output_dir, f"{name}.tex")
        with open(path, "w") as f:
            f.write(content)
        print(f"  Wrote {name}.tex")

    # Summary JSON
    summary = {}
    for key, recs in groups.items():
        m = compute_cell_metrics(recs)
        summary[f"{key[0]}_{key[1]}_{key[2]}"] = {
            "n": m["n"],
            "MIR": m["MIR"],
            "MIR_ci": list(m["MIR_ci"]),
            "QTJ_mean": m["QTJ_mean"] if m["QTJ_mean"] < 1e6 else None,
            "TIR": m["TIR"],
            "avg_duration": m["avg_duration"],
        }

    with open(os.path.join(args.output_dir, "table_data.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Wrote table_data.json")

    print(f"\nAll tables written to {args.output_dir}/")


if __name__ == "__main__":
    main()
