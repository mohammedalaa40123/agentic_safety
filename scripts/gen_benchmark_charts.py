"""
gen_benchmark_charts.py — Strict PAIR Mini-Benchmark Chart Pipeline
=====================================================================
Reads result JSONs, applies the benchmark filter (PAIR attack, no-defense,
consistent judge, 4-model core set), and emits:
  • docs/assets/charts/  — PNG chart images (embedded in README + docs)
  • docs/assets/charts/benchmark_data.json — normalised chart data file

Usage:
    python scripts/gen_benchmark_charts.py [--results-dir RESULTS_DIR] [--out-dir OUT_DIR]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import glob
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# Benchmark filter constants
# ---------------------------------------------------------------------------

BENCHMARK_ATTACK = "pair"
BENCHMARK_JUDGES = {
    "genai_rcac:llama3.3:70b",
    "genai:llama3.3:70b",
    "ollama:nemotron-3-super",
}

# Canonical 4-model core set — display names → target_model substrings
CORE_MODELS: Dict[str, str] = {
    "Llama-3.3-70B":   "llama3.3:70b",
    "DeepSeek-R1-70B": "deepseek-r1:70b",
    "DeepSeek-R1-14B": "deepseek-r1:14b",
    "DeepSeek-V3.2":   "deepseek-v3.2",
}

# Short labels for x-axis (no newlines — rotated 30° instead)
OWASP_LABEL_MAP = {
    "AAI01-BrokenAccessControl":     "AAI-01 Access Control",
    "AAI02-AgentImpersonation":      "AAI-02 Impersonation",
    "AAI03-PromptInjection":         "AAI-03 Prompt Injection",
    "AAI04-OverlyPermissiveTool":    "AAI-04 Permissive Tool",
    "AAI05-MemoryPoisoning":         "AAI-05 Memory Poison",
    "AAI06-MultiAgentExploitation":  "AAI-06 Multi-Agent",
    "AAI07-DataExfiltration":        "AAI-07 Exfiltration",
    "AAI08-ResourceAbuse":           "AAI-08 Resource Abuse",
    "AAI09-SupplyChainAttack":       "AAI-09 Supply Chain",
    "AAI10-TrustBoundaryViolation":  "AAI-10 Trust Boundary",
}

# Canonical OWASP category order
OWASP_ORDER = [
    "AAI01-BrokenAccessControl",
    "AAI02-AgentImpersonation",
    "AAI03-PromptInjection",
    "AAI04-OverlyPermissiveTool",
    "AAI05-MemoryPoisoning",
    "AAI06-MultiAgentExploitation",
    "AAI07-DataExfiltration",
    "AAI08-ResourceAbuse",
    "AAI09-SupplyChainAttack",
    "AAI10-TrustBoundaryViolation",
]

# Academic-safe palette: distinguishable on white bg, print-friendly
PALETTE = {
    "Llama-3.3-70B":   "#2166AC",   # strong blue
    "DeepSeek-R1-70B": "#D6604D",   # muted red
    "DeepSeek-R1-14B": "#1A9850",   # green
    "DeepSeek-V3.2":   "#F4A82E",   # amber
}

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    """White-background academic theme — suitable for papers and light-mode docs."""
    plt.rcParams.update({
        "figure.facecolor":   "white",
        "axes.facecolor":     "white",
        "axes.edgecolor":     "#444444",
        "axes.labelcolor":    "#222222",
        "axes.titlecolor":    "#111111",
        "xtick.color":        "#333333",
        "ytick.color":        "#333333",
        "text.color":         "#222222",
        "grid.color":         "#CCCCCC",
        "grid.linewidth":     0.6,
        "legend.facecolor":   "white",
        "legend.edgecolor":   "#AAAAAA",
        "legend.framealpha":  0.9,
        "font.family":        "sans-serif",
        "font.size":          11,
        "axes.titlesize":     13,
        "axes.titleweight":   "bold",
        "figure.dpi":         150,
        "savefig.facecolor":  "white",
        "savefig.edgecolor":  "white",
    })


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _model_key(target_model: str) -> Optional[str]:
    """Map a raw target_model string to a display name, or None if not core."""
    t = (target_model or "").lower()
    for display, substr in CORE_MODELS.items():
        if substr.lower() in t:
            return display
    return None


def _coerce_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def _coerce_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _coerce_float(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return default if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return default


def load_records(results_dir: str) -> List[Dict[str, Any]]:
    """
    Walk results_dir/**/*.json, parse every record, and return all that pass
    the strict PAIR benchmark filter (correct attack, judge in allowed set,
    no defense, core model).
    """
    pattern = os.path.join(results_dir, "**", "*.json")
    json_files = sorted(glob.glob(pattern, recursive=True))

    all_records: List[Dict[str, Any]] = []
    seen_goals: Dict[str, set] = defaultdict(set)  # model → dedup set

    for fpath in json_files:
        try:
            with open(fpath, encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            continue

        # Support both old (list) and new (dict with "records" key) schemas
        if isinstance(raw, dict):
            records_raw = raw.get("records", [])
        elif isinstance(raw, list):
            records_raw = raw
        else:
            continue

        for rec in records_raw:
            attack = (rec.get("attack_name") or "").lower().strip()
            if attack != BENCHMARK_ATTACK:
                continue

            judge = (rec.get("judge_model") or "").strip()
            target = (rec.get("target_model") or "").strip()
            defense = (rec.get("defense_name") or "").strip()

            if defense:
                continue  # exclude defended runs

            model_key = _model_key(target)
            if model_key is None:
                continue  # not in core set

            # Dedup: same model + goal pair keeps only first occurrence
            goal = rec.get("goal", "")
            if goal in seen_goals[model_key]:
                continue
            seen_goals[model_key].add(goal)

            all_records.append({
                "model":               model_key,
                "target_model":        target,
                "judge_model":         judge,
                "goal":                goal,
                "category":            rec.get("category", "unknown"),
                "attack_success":      _coerce_bool(rec.get("attack_success", False)),
                "task_success":        _coerce_bool(rec.get("task_success", False)),
                "queries":             _coerce_int(rec.get("queries", 0)),
                "tool_calls_correct":  _coerce_int(rec.get("tool_calls_correct", 0)),
                "tool_calls_wrong":    _coerce_int(rec.get("tool_calls_wrong", 0)),
                "tool_calls_total":    _coerce_int(rec.get("tool_calls_total", 0)),
                "duration":            _coerce_float(rec.get("duration", 0.0)),
            })

    return all_records


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def asr_by_model(records: List[Dict]) -> Dict[str, float]:
    counts: Dict[str, List[bool]] = defaultdict(list)
    for r in records:
        counts[r["model"]].append(r["attack_success"])
    return {
        m: (sum(vs) / len(vs) * 100) if vs else 0.0
        for m, vs in counts.items()
    }


def asr_by_category(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """Returns {category: {model: asr%}}"""
    data: Dict[str, Dict[str, List[bool]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        cat = r["category"]
        # Normalise legacy category labels
        cat_short = cat.split("-")[0] if "-" in cat and not cat.startswith("AAI") else cat
        data[cat_short][r["model"]].append(r["attack_success"])
    return {
        cat: {
            model: (sum(vs) / len(vs) * 100) if vs else 0.0
            for model, vs in model_map.items()
        }
        for cat, model_map in data.items()
    }


def tool_quality(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """{model: {correct%, wrong%}}"""
    totals: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        t = r["tool_calls_total"]
        if t > 0:
            totals[r["model"]]["correct"].append(r["tool_calls_correct"] / t * 100)
            totals[r["model"]]["wrong"].append(r["tool_calls_wrong"] / t * 100)
    return {
        m: {
            "correct": float(np.mean(v["correct"])) if v.get("correct") else 0.0,
            "wrong":   float(np.mean(v["wrong"])) if v.get("wrong") else 0.0,
        }
        for m, v in totals.items()
    }


def query_efficiency(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """{model: {avg_queries, asr%}}"""
    buckets: Dict[str, List] = defaultdict(list)
    for r in records:
        buckets[r["model"]].append((r["queries"], r["attack_success"]))
    result = {}
    for m, pairs in buckets.items():
        qs = [p[0] for p in pairs]
        succs = [p[1] for p in pairs]
        result[m] = {
            "avg_queries": float(np.mean(qs)) if qs else 0.0,
            "asr":         (sum(succs) / len(succs) * 100) if succs else 0.0,
        }
    return result


# ---------------------------------------------------------------------------
# Chart renderers
# ---------------------------------------------------------------------------

def chart_asr_by_model(data: Dict[str, float], out_path: str) -> None:
    models = list(CORE_MODELS.keys())
    values = [data.get(m, 0.0) for m in models]
    colors = [PALETTE.get(m, "#888") for m in models]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(models, values, color=colors, width=0.55,
                  edgecolor="white", linewidth=0.5, zorder=3)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("PAIR Attack Success Rate by Target Model (No Defense)")
    ax.yaxis.grid(True, zorder=0, alpha=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{val:.0f}%",
            ha="center", va="bottom", fontsize=11, color="#222222", fontweight="bold"
        )

    ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def chart_asr_by_owasp(data: Dict[str, Dict[str, float]], out_path: str) -> None:
    # Use the canonical OWASP order; fill 0 for missing categories
    owasp_cats = OWASP_ORDER

    models = list(CORE_MODELS.keys())
    x = np.arange(len(owasp_cats))
    width = 0.20
    offsets = np.linspace(-1.5 * width, 1.5 * width, len(models))

    fig, ax = plt.subplots(figsize=(13, 5))

    for model, offset in zip(models, offsets):
        vals = [data.get(cat, {}).get(model, 0.0) for cat in owasp_cats]
        bars = ax.bar(x + offset, vals, width, label=model,
                      color=PALETTE.get(model, "#888"),
                      edgecolor="white", linewidth=0.4, zorder=3)

    # Short readable labels rotated 30° — no newlines needed
    labels = [OWASP_LABEL_MAP.get(cat, cat) for cat in owasp_cats]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=30, ha="right", rotation_mode="anchor")
    ax.set_ylim(0, 115)
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("ASR by OWASP Agentic AI Top-10 Category (PAIR, No Defense)")
    ax.yaxis.grid(True, zorder=0, alpha=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", fontsize=9, frameon=True)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def chart_tool_quality(data: Dict[str, Dict[str, float]], out_path: str) -> None:
    models = [m for m in CORE_MODELS if m in data]
    correct = [data[m]["correct"] for m in models]
    wrong   = [data[m]["wrong"]   for m in models]
    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - width / 2, correct, width, label="Correct (%)",
           color="#1A9850", edgecolor="white", linewidth=0.4, zorder=3)
    ax.bar(x + width / 2, wrong,   width, label="Wrong (%)",
           color="#D6604D", edgecolor="white", linewidth=0.4, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=10)
    ax.set_ylim(0, 110)
    ax.set_ylabel("% of Total Tool Calls")
    ax.set_title("Tool-Call Quality by Model (PAIR, No Defense)")
    ax.yaxis.grid(True, zorder=0, alpha=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def chart_query_efficiency(data: Dict[str, Dict[str, float]], out_path: str) -> None:
    models = [m for m in CORE_MODELS if m in data]
    avg_qs = [data[m]["avg_queries"] for m in models]
    asrs   = [data[m]["asr"]         for m in models]
    colors = [PALETTE.get(m, "#888") for m in models]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(avg_qs, asrs, c=colors, s=240, zorder=5,
               edgecolors="#444444", linewidths=1.0)

    for m, xv, yv in zip(models, avg_qs, asrs):
        ax.annotate(m, (xv, yv), textcoords="offset points",
                    xytext=(8, 4), fontsize=9, color="#222222")

    ax.set_xlabel("Avg Queries to Jailbreak (QTJ)")
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("Query Efficiency vs ASR (PAIR Core, No Defense)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    patches = [mpatches.Patch(color=PALETTE[m], label=m) for m in models if m in PALETTE]
    ax.legend(handles=patches, fontsize=9, loc="lower right", frameon=True)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def chart_judge_score_distribution(records: List[Dict], out_path: str) -> None:
    """Proxy: distribution of queries-per-run (judge score proxy)."""
    models = list(CORE_MODELS.keys())
    fig, axes = plt.subplots(1, len(models), figsize=(13, 4), sharey=False)

    for ax, model in zip(axes, models):
        model_recs = [r for r in records if r["model"] == model]
        qs = [r["queries"] for r in model_recs]
        if not qs:
            ax.set_visible(False)
            continue
        bins = range(1, max(qs) + 2)
        ax.hist(qs, bins=bins, align="left", color=PALETTE.get(model, "#888"),
                edgecolor="white", linewidth=0.5, zorder=3)
        ax.set_title(model, fontsize=10)
        ax.set_xlabel("Queries")
        ax.yaxis.grid(True, zorder=0, alpha=0.6)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Frequency")
    fig.suptitle("Query Count Distribution (PAIR, No Defense)", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PAIR mini-benchmark charts")
    parser.add_argument(
        "--results-dir",
        default="results/agentic_experiments_v2_500",
        help="Root directory containing experiment result sub-folders",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/assets/charts",
        help="Output directory for chart PNGs and normalised JSON",
    )
    args = parser.parse_args()

    apply_theme()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔍  Loading records from: {args.results_dir}")
    records = load_records(args.results_dir)
    print(f"    Loaded {len(records)} benchmark records across {len(CORE_MODELS)} core models.")

    if not records:
        print("⚠️  No records matched the strict PAIR benchmark filter. Check results dir.")
        sys.exit(1)

    model_counts = defaultdict(int)
    for r in records:
        model_counts[r["model"]] += 1
    print("    Per-model counts:", dict(model_counts))

    # ---- Aggregations ----
    asr_model_data   = asr_by_model(records)
    asr_owasp_data   = asr_by_category(records)
    tool_data        = tool_quality(records)
    qeff_data        = query_efficiency(records)

    # ---- Charts ----
    print("\n📊  Generating charts ...")
    chart_asr_by_model(asr_model_data,            str(out_dir / "asr_by_model.png"))
    chart_asr_by_owasp(asr_owasp_data,            str(out_dir / "asr_by_category.png"))
    chart_tool_quality(tool_data,                 str(out_dir / "tool_quality.png"))
    chart_query_efficiency(qeff_data,             str(out_dir / "query_efficiency.png"))
    chart_judge_score_distribution(records,       str(out_dir / "query_distribution.png"))

    # ---- Normalised data file ----
    benchmark_data = {
        "benchmark": {
            "attack":       BENCHMARK_ATTACK,
            "defense":      "none",
            "judge_set":    sorted(BENCHMARK_JUDGES),
            "core_models":  list(CORE_MODELS.keys()),
            "total_records": len(records),
            "per_model_n":  dict(model_counts),
        },
        "asr_by_model":     asr_model_data,
        "asr_by_category":  {
            cat: vals for cat, vals in sorted(asr_owasp_data.items())
        },
        "tool_quality":     tool_data,
        "query_efficiency": qeff_data,
    }

    data_path = out_dir / "benchmark_data.json"
    with open(data_path, "w") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"  ✓ {data_path}")

    print("\n✅  Done. All assets written to:", out_dir)
    print("\nPer-model ASR summary:")
    for m, asr in asr_model_data.items():
        print(f"  {m:20s}  {asr:.1f}%")


if __name__ == "__main__":
    main()
