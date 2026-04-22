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

# Extended models — shown in category and scatter charts only for diversity
# These are smaller / older models used to contrast the core 4
EXTENDED_MODELS: Dict[str, str] = {
    "Qwen3-1.7B":      "qwen3:1.7b",
    "DeepSeek-R1-7B":  "deepseek-r1:7b",
    "Llama-3.1":       "llama3.1:latest",
}

ALL_MODELS: Dict[str, str] = {**CORE_MODELS, **EXTENDED_MODELS}

# Short labels for x-axis (no newlines — rotated 30° instead)
# Keys must match the actual category strings present in result JSONs
OWASP_LABEL_MAP = {
    "AAI01-BrokenAccessControl":   "AAI-01 Broken Access",
    "AAI02-PromptInjection":       "AAI-02 Prompt Injection",
    "AAI03-ExcessiveAgency":       "AAI-03 Excessive Agency",
    "AAI04-ModelHallucination":    "AAI-04 Hallucination",
    "AAI05-ImpactChain":           "AAI-05 Impact Chain",
    "AAI06-MemoryContextPoisoning":"AAI-06 Memory Poisoning",
    "AAI07-InsecureOrchestration": "AAI-07 Orchestration",
    "AAI08-ResourceExhaustion":    "AAI-08 Resource Exhaust",
    "AAI09-SupplyChain":           "AAI-09 Supply Chain",
    "AAI10-KnowledgePoisoning":    "AAI-10 Knowledge Poison",
    # legacy / agent-level label
    "agent":                       "agent",
}

# Canonical order for the chart — matches actual keys
OWASP_ORDER = [
    "AAI01-BrokenAccessControl",
    "AAI02-PromptInjection",
    "AAI03-ExcessiveAgency",
    "AAI04-ModelHallucination",
    "AAI05-ImpactChain",
    "AAI06-MemoryContextPoisoning",
    "AAI07-InsecureOrchestration",
    "AAI08-ResourceExhaustion",
    "AAI09-SupplyChain",
    "AAI10-KnowledgePoisoning",
]

# Academic-safe palette: distinguishable on white bg, print-friendly
PALETTE = {
    "Llama-3.3-70B":   "#2166AC",   # strong blue
    "DeepSeek-R1-70B": "#D6604D",   # muted red
    "DeepSeek-R1-14B": "#1A9850",   # green
    "DeepSeek-V3.2":   "#F4A82E",   # amber
    # Extended — muted/lighter variants
    "Qwen3-1.7B":      "#762A83",   # purple
    "DeepSeek-R1-7B":  "#018571",   # teal
    "Llama-3.1":       "#B35806",   # brown-orange
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

def _model_key(target_model: str,
               models: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Map a raw target_model string to a display name, or None if not in models."""
    if models is None:
        models = CORE_MODELS
    t = (target_model or "").lower()
    for display, substr in models.items():
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


def load_records(results_dir: str,
                 models: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Walk results_dir/**/*.json, parse every record, and return all that pass
    the strict PAIR benchmark filter (correct attack, judge in allowed set,
    no defense, models in the given models dict).
    """
    if models is None:
        models = CORE_MODELS

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

            model_key = _model_key(target, models)
            if model_key is None:
                continue  # not in specified model set

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

def mir_by_model(records: List[Dict]) -> Dict[str, float]:
    counts: Dict[str, List[bool]] = defaultdict(list)
    for r in records:
        counts[r["model"]].append(r["attack_success"])
    return {
        m: (sum(vs) / len(vs) * 100) if vs else 0.0
        for m, vs in counts.items()
    }


def mir_by_category(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """Returns {category: {model: mir%}}"""
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
    """{model: {avg_queries, mir%}}"""
    buckets: Dict[str, List] = defaultdict(list)
    for r in records:
        buckets[r["model"]].append((r["queries"], r["attack_success"]))
    result = {}
    for m, pairs in buckets.items():
        qs = [p[0] for p in pairs]
        succs = [p[1] for p in pairs]
        result[m] = {
            "avg_queries": float(np.mean(qs)) if qs else 0.0,
            "mir":         (sum(succs) / len(succs) * 100) if succs else 0.0,
        }
    return result


# ---------------------------------------------------------------------------
# Chart renderers
# ---------------------------------------------------------------------------

def chart_mir_by_model(data: Dict[str, float], out_path: str) -> None:
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


def chart_mir_by_owasp(data: Dict[str, Dict[str, float]],
                       out_path: str,
                       ext_data: Optional[Dict[str, Dict[str, float]]] = None) -> None:
    """
    Grouped bar chart: MIR per OWASP category.
    Core models use solid bars; extended models use hatched bars.
    ext_data: optional {category: {model: mir%}} for extended models.
    """
    owasp_cats = OWASP_ORDER

    core_models = list(CORE_MODELS.keys())
    ext_models  = list(EXTENDED_MODELS.keys()) if ext_data else []
    all_disp    = core_models + ext_models

    n_groups = len(all_disp)
    total_width = 0.80          # total bar-group width per category tick
    width = total_width / n_groups
    offsets = np.linspace(-(n_groups - 1) / 2 * width,
                          (n_groups - 1) / 2 * width,
                          n_groups)

    x = np.arange(len(owasp_cats))
    fig, ax = plt.subplots(figsize=(14, 5.5))

    for model, offset in zip(core_models, offsets[:len(core_models)]):
        vals = [data.get(cat, {}).get(model, 0.0) for cat in owasp_cats]
        ax.bar(x + offset, vals, width, label=model,
               color=PALETTE.get(model, "#888"),
               edgecolor="white", linewidth=0.4, zorder=3)

    if ext_data:
        for model, offset in zip(ext_models, offsets[len(core_models):]):
            vals = [ext_data.get(cat, {}).get(model, 0.0) for cat in owasp_cats]
            ax.bar(x + offset, vals, width,
                   label=f"{model} \u25a6",          # ▦ marker in legend
                   color=PALETTE.get(model, "#aaa"),
                   edgecolor="white", linewidth=0.4,
                   hatch="///", alpha=0.75, zorder=3)

    labels = [OWASP_LABEL_MAP.get(cat, cat) for cat in owasp_cats]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5, rotation=30,
                       ha="right", rotation_mode="anchor")
    ax.set_ylim(0, 120)
    ax.set_ylabel("Attack Success Rate (%)")
    title = "MIR by OWASP Agentic AI Top-10 Category (PAIR, No Defense)"
    if ext_data:
        title += "  [▦ = small/older models]"
    ax.set_title(title, fontsize=12)
    ax.yaxis.grid(True, zorder=0, alpha=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", fontsize=8.5, frameon=True, ncol=2)

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


def chart_query_efficiency(data: Dict[str, Dict[str, float]],
                           out_path: str,
                           ext_data: Optional[Dict[str, Dict[str, float]]] = None) -> None:
    """
    Scatter: avg QTJ vs MIR per model.
    Core models: filled circles. Extended models: hollow diamonds.
    Labels connected with arrows to avoid collision.
    """
    core_models = [m for m in CORE_MODELS if m in data]
    ext_models  = [m for m in EXTENDED_MODELS if ext_data and m in ext_data] if ext_data else []

    all_models  = core_models + ext_models
    all_x = [data[m]["avg_queries"] for m in core_models] + \
            ([ext_data[m]["avg_queries"] for m in ext_models] if ext_data else [])
    all_y = [data[m]["mir"] for m in core_models] + \
            ([ext_data[m]["mir"] for m in ext_models] if ext_data else [])
    all_c = [PALETTE.get(m, "#888") for m in all_models]

    fig, ax = plt.subplots(figsize=(8, 6))

    # Core: filled circles
    cx = [data[m]["avg_queries"] for m in core_models]
    cy = [data[m]["mir"]         for m in core_models]
    cc = [PALETTE.get(m, "#888") for m in core_models]
    ax.scatter(cx, cy, c=cc, s=260, zorder=5, edgecolors="#333333", linewidths=1.0,
               marker="o", label="Core (4 model)")

    # Extended: hollow diamonds
    if ext_data and ext_models:
        ex = [ext_data[m]["avg_queries"] for m in ext_models]
        ey = [ext_data[m]["mir"]         for m in ext_models]
        ec = [PALETTE.get(m, "#888") for m in ext_models]
        for xv, yv, col in zip(ex, ey, ec):
            # Outer ring diamond (colored edge, white fill)
            ax.scatter(xv, yv, s=260, zorder=5,
                       edgecolors=col, linewidths=2.0,
                       marker="D", facecolors="white")
            # Small inner fill dot so the color is visible
            ax.scatter(xv, yv, s=70, zorder=6,
                       edgecolors="none", facecolors=col, marker="D")

    # ---- Arrow annotations with automatic repulsion ----
    # Place text labels in a "ring" around the cluster
    xs = np.array(all_x, dtype=float)
    ys = np.array(all_y, dtype=float)

    # Compute centre of mass of all points
    cx_mean = float(np.mean(xs))
    cy_mean = float(np.mean(ys))

    # Text position = data point pushed outward from centre by a fixed amount
    x_range = max(xs) - min(xs) if len(xs) > 1 else 1.0
    y_range = max(ys) - min(ys) if len(ys) > 1 else 1.0
    push_x = max(x_range * 0.80, 0.55)
    push_y = max(y_range * 0.80, 12.0)

    for m, xv, yv in zip(all_models, all_x, all_y):
        dx = xv - cx_mean
        dy = yv - cy_mean
        norm = math.sqrt(dx**2 + dy**2) or 1.0
        tx = xv + (dx / norm) * push_x
        ty = yv + (dy / norm) * push_y
        # Clamp text inside axes limits
        tx = max(0.05, tx)
        ty = max(5.0, min(108.0, ty))
        ax.annotate(
            m, xy=(xv, yv), xytext=(tx, ty),
            fontsize=8.5, color="#222222",
            arrowprops=dict(arrowstyle="->", color="#666666",
                            lw=0.8, shrinkA=0, shrinkB=4),
            ha="center", va="center",
        )

    ax.set_xlabel("Avg Queries to Jailbreak (QTJ)")
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("Query Efficiency vs MIR (PAIR, No Defense)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 115)
    ax.grid(True, alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend: solid patch = core, hollow diamond = extended
    patches = [mpatches.Patch(color=PALETTE[m], label=m)
               for m in all_models if m in PALETTE]
    ax.legend(handles=patches, fontsize=8.5, loc="lower right",
              frameon=True, ncol=1 if len(patches) <= 4 else 2)

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
    records = load_records(args.results_dir, models=CORE_MODELS)
    print(f"    Loaded {len(records)} benchmark records across {len(CORE_MODELS)} core models.")

    if not records:
        print("⚠️  No records matched the strict PAIR benchmark filter. Check results dir.")
        sys.exit(1)

    # Also load extended models (for diversity charts)
    ext_records = load_records(args.results_dir, models=EXTENDED_MODELS)
    print(f"    Loaded {len(ext_records)} extended records "
          f"({', '.join(EXTENDED_MODELS.keys())}).")

    model_counts = defaultdict(int)
    for r in records:
        model_counts[r["model"]] += 1
    print("    Per-model counts:", dict(model_counts))

    # ---- Aggregations ----
    mir_model_data   = mir_by_model(records)
    mir_owasp_data   = mir_by_category(records)
    ext_owasp_data   = mir_by_category(ext_records) if ext_records else None
    tool_data        = tool_quality(records)
    qeff_data        = query_efficiency(records)
    ext_qeff_data    = query_efficiency(ext_records) if ext_records else None

    # ---- Charts ----
    print("\n📊  Generating charts ...")
    chart_mir_by_model(mir_model_data,            str(out_dir / "mir_by_model.png"))
    chart_mir_by_owasp(mir_owasp_data,            str(out_dir / "mir_by_category.png"),
                       ext_data=ext_owasp_data)
    chart_tool_quality(tool_data,                 str(out_dir / "tool_quality.png"))
    chart_query_efficiency(qeff_data,             str(out_dir / "query_efficiency.png"),
                           ext_data=ext_qeff_data)
    chart_judge_score_distribution(records,       str(out_dir / "query_distribution.png"))

    # ---- Normalised data file ----
    benchmark_data = {
        "benchmark": {
            "attack":        BENCHMARK_ATTACK,
            "defense":       "none",
            "judge_set":     sorted(BENCHMARK_JUDGES),
            "core_models":   list(CORE_MODELS.keys()),
            "extended_models": list(EXTENDED_MODELS.keys()),
            "total_records": len(records),
            "per_model_n":   dict(model_counts),
        },
        "mir_by_model":     mir_model_data,
        "mir_by_category":  {
            cat: vals for cat, vals in sorted(mir_owasp_data.items())
        },
        "tool_quality":     tool_data,
        "query_efficiency": qeff_data,
    }

    data_path = out_dir / "benchmark_data.json"
    with open(data_path, "w") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"  ✓ {data_path}")

    print("\n✅  Done. All assets written to:", out_dir)
    print("\nPer-model MIR summary (core):")
    for m, mir in mir_model_data.items():
        print(f"  {m:20s}  {mir:.1f}%")
    if ext_qeff_data:
        print("\nExtended model query efficiency:")
        for m, v in ext_qeff_data.items():
            print(f"  {m:20s}  MIR={v['mir']:.1f}%  QTJ={v['avg_queries']:.2f}")


if __name__ == "__main__":
    main()
