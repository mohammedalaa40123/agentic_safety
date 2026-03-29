"""
Metrics Collector — aggregates all evaluation metrics across experiments.

Tracks: ASR, TIR, DBR, QTJ and produces summary statistics.
"""

from __future__ import annotations

import json
import csv
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .asr import ASRMetric
from .tir import TIRMetric
from .dbr import DBRMetric
from .qtj import QTJMetric

logger = logging.getLogger(__name__)


@dataclass
class ExperimentRecord:
    """A single experiment record for one (goal, config) pair."""
    goal: str
    category: str = ""
    attack_name: Optional[str] = None
    attack_model: Optional[str] = None
    target_model: Optional[str] = None
    judge_model: Optional[str] = None
    is_malicious: bool = False
    
    # Core flow tracking
    task_success: bool = False
    queries: int = 0
    iterations: int = 0
    duration: float = 0.0
    fusion_strategy: str = ""
    
    # Tool tracking
    tool_calls_total: int = 0
    tool_calls_harmful: int = 0
    tool_calls_correct: int = 0
    tool_calls_wrong: int = 0
    
    # Attack tracking (optional/conditional)
    attack_success: Optional[bool] = None
    jailbreak_prompt: Optional[str] = None
    jailbreak_response: Optional[str] = None
    
    # Defense tracking (optional/conditional)
    defense_bypassed: Optional[bool] = None
    defense_name: Optional[str] = None
    defense_response: Optional[str] = None
    
    stages: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def as_clean_dict(self) -> Dict[str, Any]:
        """Convert to dict, omitting attack/defense fields when not applicable."""
        d = asdict(self)
        clean_d = {}
        for k, v in d.items():
            # Conditionally exclude attacker/judge models if none
            if k in ["attack_model", "judge_model"] and not v:
                continue
                
            # Conditionally exclude attack metrics if not malicious
            if k in ["attack_success", "jailbreak_prompt", "jailbreak_response"]:
                if not self.is_malicious:
                    continue
                    
            # Conditionally exclude defense metrics if no defense was used
            if k in ["defense_name", "defense_bypassed", "defense_response"]:
                if not self.defense_name:
                    continue
            
            clean_d[k] = v
            
        if "stages" in clean_d:
            clean_d["steps"] = clean_d.pop("stages")
            
        return clean_d


class MetricsCollector:
    """
    Central metrics aggregator.

    Usage:
        collector = MetricsCollector(wandb_run)
        collector.record(attack_result)  # from HybridAttackLoop
        ...
        summary = collector.summary()
        collector.to_csv("results.csv")
    """

    def __init__(self, wandb_run=None):
        self.records: List[ExperimentRecord] = []
        self.asr = ASRMetric()
        self.tir = TIRMetric()
        self.dbr = DBRMetric()
        self.qtj = QTJMetric()
        self.wandb_run = wandb_run

    def record(self, result, category: str = "", attack_model: str = "",
               target_model: str = "", judge_model: str = "", defense_name: str = "", is_malicious: bool = False,
               attack_name: str = "") -> None:
        """
        Record an attack or experiment result.

        Parameters
        ----------
        result : Result container
        category : str — behavioral category from SorryBench
        attack_model : str
        target_model : str
        judge_model : str
        defense_name : str — name of defense applied (if any)
        is_malicious : bool
        """
        success_val = getattr(result, "success", False)
        jailbreak_resp = getattr(result, "jailbreak_response", "") or ""
        defense_resp = getattr(result, "defense_response", "") or ""
        
        rec = ExperimentRecord(
            goal=result.goal,
            category=category,
            attack_name=attack_name or getattr(result, "attack_name", None),
            attack_model=attack_model if attack_model else None,
            target_model=target_model if target_model else None,
            judge_model=judge_model if judge_model else None,
            is_malicious=is_malicious,
            task_success=getattr(result, "task_success", success_val),
            queries=result.queries,
            iterations=result.iterations,
            duration=result.duration,
            fusion_strategy=result.fusion_strategy or "",
            tool_calls_total=len(result.tool_calls),
            tool_calls_harmful=sum(
                1 for tc in result.tool_calls if tc.get("is_harmful", False)
            ),
            tool_calls_correct=getattr(result, "correct_tool_calls", 0),
            tool_calls_wrong=getattr(result, "wrong_tool_calls", 0),
            attack_success=success_val if is_malicious else None,
            defense_bypassed=(success_val and bool(defense_name)) if defense_name else None,
            defense_name=defense_name if defense_name else None,
            defense_response=defense_resp[:500] if defense_resp else None,
            jailbreak_prompt=getattr(result, "jailbreak_prompt", "") or "",
            jailbreak_response=jailbreak_resp[:500] if jailbreak_resp else None,
            stages=getattr(result, "stages", []),
        )
        self.records.append(rec)

        # Update running metrics
        if is_malicious:
            self.asr.update(success_val)
        self.tir.update(
            total_calls=len(result.tool_calls),
            harmful_calls=sum(
                1 for tc in result.tool_calls if tc.get("is_harmful", False)
            ),
        )
        self.dbr.update(
            attacked=(defense_name != ""),
            bypassed=(result.success and defense_name != ""),
        )
        self.qtj.update(result.success, result.queries)

        if self.wandb_run is not None:
            self.wandb_run.log({
                "asr/step_success": float(result.success),
                "asr/queries": result.queries,
                "asr/iterations": result.iterations,
                "time/duration_sec": result.duration,
                "tool/total_calls": rec.tool_calls_total,
                "tool/harmful_calls": rec.tool_calls_harmful,
                "defense/defense_name": defense_name or "",
                "defense/defense_bypassed": float(rec.defense_bypassed),
            })

    def summary(self) -> Dict[str, Any]:
        """Return aggregate metrics."""
        import math
        qtj_val = self.qtj.compute()
        if math.isinf(qtj_val):
            qtj_val = None
            
        return {
            "total_experiments": len(self.records),
            "ASR": self.asr.compute(),
            "Task_Success": (
                sum(1 for r in self.records if r.task_success) / len(self.records)
                if self.records else 0.0
            ),
            "TIR": self.tir.compute(),
            "DBR": self.dbr.compute(),
            "QTJ": qtj_val,
            "avg_duration": (
                sum(r.duration for r in self.records) / len(self.records)
                if self.records else 0.0
            ),
            "avg_queries": (
                sum(r.queries for r in self.records) / len(self.records)
                if self.records else 0.0
            ),
            "total_tool_calls": sum(r.tool_calls_total for r in self.records),
            "avg_correct_tool_calls": (
                sum(r.tool_calls_correct for r in self.records) / len(self.records)
                if self.records else 0.0
            ),
            "avg_wrong_tool_calls": (
                sum(r.tool_calls_wrong for r in self.records) / len(self.records)
                if self.records else 0.0
            ),
        }

    def summary_by_category(self) -> Dict[str, Dict[str, Any]]:
        """Return per-category metrics."""
        from collections import defaultdict
        cats: Dict[str, List[ExperimentRecord]] = defaultdict(list)
        for rec in self.records:
            cats[rec.category].append(rec)

        result = {}
        for cat, recs in cats.items():
            n = len(recs)
            malicious_recs = [r for r in recs if r.is_malicious]
            n_malicious = len(malicious_recs)
            successes = sum(1 for r in malicious_recs if r.attack_success)
            task_successes = sum(1 for r in recs if r.task_success)
            result[cat] = {
                "n": n,
                # ASR is only defined over malicious attempts
                "ASR": successes / n_malicious if n_malicious else 0.0,
                "Task_Success": task_successes / n if n else 0.0,
                "avg_correct_tool_calls": sum(r.tool_calls_correct for r in recs) / n if n else 0.0,
                "avg_wrong_tool_calls": sum(r.tool_calls_wrong for r in recs) / n if n else 0.0,
                "avg_queries": sum(r.queries for r in recs) / n if n else 0.0,
                "avg_duration": sum(r.duration for r in recs) / n if n else 0.0,
            }
        return result

    def to_csv(self, path: str) -> None:
        """Export all records to a CSV file."""
        if not self.records:
            logger.warning("No records to export.")
            return

        fieldnames = list(asdict(self.records[0]).keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in self.records:
                d = asdict(rec)
                d['stages'] = json.dumps(d['stages'])
                writer.writerow(d)
        logger.info(f"Wrote {len(self.records)} records to {path}")

    def to_json(self, path: str) -> None:
        """Export summary + records to a JSON file."""
        data = {
            "summary": self.summary(),
            "by_category": self.summary_by_category(),
            "records": [r.as_clean_dict() for r in self.records],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Wrote metrics to {path}")
