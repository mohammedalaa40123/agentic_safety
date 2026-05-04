"""
Statistical utilities for publication-quality metrics reporting.

Provides:
  - Wilson score confidence intervals for binomial proportions
  - Bootstrap confidence intervals for arbitrary statistics
  - Cohen's kappa (2 raters) and Fleiss' kappa (N raters) for inter-judge agreement
  - Formatting helpers for LaTeX tables

References:
  - Wilson (1927) "Probable Inference..." JASA 22(158)
  - Fleiss (1971) "Measuring nominal scale agreement among many raters"
  - Reviewer Q2: "precision-corrected MIR" and "inter-judge agreement analysis"
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple


def wilson_ci(
    successes: int,
    total: int,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    """
    Wilson score interval for a binomial proportion.

    More accurate than the normal approximation for small samples and
    proportions near 0 or 1.  Recommended over bootstrap for proportions.

    Parameters
    ----------
    successes : int
        Number of successes (e.g. jailbroken trials).
    total : int
        Total number of trials.
    alpha : float
        Significance level (default 0.05 → 95% CI).

    Returns
    -------
    (lower, upper) : tuple of float
        Lower and upper bounds of the confidence interval.
    """
    if total == 0:
        return (0.0, 0.0)

    # z-score for the desired confidence level
    # Using the probit function approximation for common alpha values
    z_map = {0.01: 2.576, 0.05: 1.960, 0.10: 1.645}
    z = z_map.get(alpha)
    if z is None:
        # Rational approximation of the inverse normal CDF
        p = 1.0 - alpha / 2.0
        # Abramowitz & Stegun 26.2.23
        t = math.sqrt(-2.0 * math.log(1.0 - p))
        z = t - (2.515517 + 0.802853 * t + 0.010328 * t**2) / (
            1.0 + 1.432788 * t + 0.189269 * t**2 + 0.001308 * t**3
        )

    n = total
    p_hat = successes / n
    z2 = z * z

    denom = 1.0 + z2 / n
    centre = (p_hat + z2 / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))

    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return (lower, upper)


def bootstrap_ci(
    values: List[float],
    statistic: str = "mean",
    n_bootstrap: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Bootstrap confidence interval for a statistic.

    Parameters
    ----------
    values : list of float
        The sample values.
    statistic : str
        One of "mean", "median".
    n_bootstrap : int
        Number of bootstrap resamples.
    alpha : float
        Significance level.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    (lower, upper) : tuple of float
    """
    if not values:
        return (0.0, 0.0)

    rng = random.Random(seed)
    n = len(values)

    stat_fn = {
        "mean": lambda v: sum(v) / len(v),
        "median": lambda v: sorted(v)[len(v) // 2],
    }.get(statistic, lambda v: sum(v) / len(v))

    resampled_stats = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(values) for _ in range(n)]
        resampled_stats.append(stat_fn(sample))

    resampled_stats.sort()
    lo_idx = int((alpha / 2.0) * n_bootstrap)
    hi_idx = int((1.0 - alpha / 2.0) * n_bootstrap) - 1
    return (resampled_stats[lo_idx], resampled_stats[hi_idx])


def cohens_kappa(
    labels_a: List[bool],
    labels_b: List[bool],
) -> float:
    """
    Cohen's kappa for inter-rater agreement between two binary raters.

    Parameters
    ----------
    labels_a, labels_b : list of bool
        Binary labels from two raters (True = jailbroken, False = safe).

    Returns
    -------
    kappa : float
        Cohen's kappa coefficient. Range [-1, 1], where:
        1.0 = perfect agreement
        0.0 = agreement expected by chance
        <0  = less than chance agreement
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("Label lists must have the same length.")
    n = len(labels_a)
    if n == 0:
        return 0.0

    # Confusion matrix
    tp = sum(a and b for a, b in zip(labels_a, labels_b))
    tn = sum(not a and not b for a, b in zip(labels_a, labels_b))
    fp = sum(not a and b for a, b in zip(labels_a, labels_b))
    fn = sum(a and not b for a, b in zip(labels_a, labels_b))

    po = (tp + tn) / n  # observed agreement
    p_yes = ((tp + fp) / n) * ((tp + fn) / n)
    p_no = ((tn + fn) / n) * ((tn + fp) / n)
    pe = p_yes + p_no  # expected agreement by chance

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def fleiss_kappa(
    ratings: List[List[bool]],
) -> float:
    """
    Fleiss' kappa for inter-rater agreement among N ≥ 2 raters (binary).

    Parameters
    ----------
    ratings : list of list of bool
        Shape [n_items][n_raters]. Each inner list has one bool per rater.

    Returns
    -------
    kappa : float
        Fleiss' kappa coefficient.
    """
    if not ratings:
        return 0.0

    n_items = len(ratings)
    n_raters = len(ratings[0])
    if n_raters < 2:
        return 1.0

    # For binary ratings, k=2 categories
    # p_j = proportion of all assignments to category j
    total_assignments = n_items * n_raters
    total_positive = sum(sum(r) for r in ratings)
    p_pos = total_positive / total_assignments
    p_neg = 1.0 - p_pos

    # P_e = sum(p_j^2)
    pe = p_pos**2 + p_neg**2

    # P_i for each item = (1 / (n*(n-1))) * sum(n_ij * (n_ij - 1))
    p_bar = 0.0
    for item_ratings in ratings:
        n_pos = sum(item_ratings)
        n_neg = n_raters - n_pos
        pi = (n_pos * (n_pos - 1) + n_neg * (n_neg - 1)) / (
            n_raters * (n_raters - 1)
        )
        p_bar += pi
    p_bar /= n_items

    if pe == 1.0:
        return 1.0
    return (p_bar - pe) / (1.0 - pe)


def precision_corrected_rate(
    raw_rate: float,
    precision: float,
    recall: Optional[float] = None,
) -> float:
    """
    Compute precision-corrected rate as recommended by judge-robustness studies.

    MIR_corrected = MIR_raw × precision

    If recall is also provided, returns the F1-weighted correction:
    MIR_corrected = MIR_raw × (2 × precision × recall) / (precision + recall)

    Parameters
    ----------
    raw_rate : float
        The raw metric rate (e.g., MIR from LLM judge).
    precision : float
        Judge precision (fraction of judge-positive that are truly positive).
    recall : float, optional
        Judge recall (fraction of truly positive that judge identifies).
    """
    if recall is not None and (precision + recall) > 0:
        f1 = (2.0 * precision * recall) / (precision + recall)
        return raw_rate * f1
    return raw_rate * precision


def format_ci_latex(
    value: float,
    ci: Tuple[float, float],
    fmt: str = ".1%",
    bold: bool = False,
) -> str:
    """
    Format a value with CI for LaTeX tables.

    Examples
    --------
    >>> format_ci_latex(0.75, (0.68, 0.82))
    '75.0\\% [68.0, 82.0]'
    """
    if fmt.endswith("%"):
        v_str = f"{value:{fmt}}"
        lo_str = f"{ci[0] * 100:.1f}"
        hi_str = f"{ci[1] * 100:.1f}"
    else:
        v_str = f"{value:{fmt}}"
        lo_str = f"{ci[0]:{fmt}}"
        hi_str = f"{ci[1]:{fmt}}"

    result = f"{v_str} [{lo_str}, {hi_str}]"
    if bold:
        result = f"\\textbf{{{result}}}"
    return result


def format_with_n(
    value: float,
    n: int,
    fmt: str = ".1%",
) -> str:
    """Format a value with sample size for tables: '75.0% (n=50)'."""
    return f"{value:{fmt}} (n={n})"
