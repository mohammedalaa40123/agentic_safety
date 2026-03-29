import logging
import os
import sys
import time
from typing import List

from .config import RunConfig, AttackSpec


def setup_logging(cfg: RunConfig) -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(cfg.output_dir, f"{cfg.experiment_name}_{timestamp}.log")

    log_level_console = logging.DEBUG if cfg.logging.verbose else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level_console)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    os.makedirs(cfg.output_dir, exist_ok=True)
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    return log_file


def format_attack_list(attacks: List[AttackSpec]) -> str:
    enabled = [a for a in attacks if a.enabled]
    return ", ".join([f"{a.name}(stop={a.stop_on_success})" for a in enabled]) or "none"


def log_run_header(logger: logging.Logger, cfg: RunConfig, log_file: str, output_paths: str = "") -> None:
    logger.info("=" * 60)
    logger.info("Agentic Safety Evaluation — Starting Experiment")
    logger.info("=" * 60)
    logger.info(f"Mode         : {cfg.mode}")
    logger.info(f"Attack model : {cfg.models.attack_model}")
    logger.info(f"Target model : {cfg.models.target_model}")
    logger.info(f"Judge model  : {cfg.models.judge_model}")
    logger.info(f"Sandbox      : {cfg.sandbox.enabled}")
    logger.info(f"Defenses     : {cfg.defenses.active if cfg.defenses.enabled else []}")
    logger.info(f"Attacks      : {format_attack_list(cfg.attacks)}")
    logger.info(f"Baseline     : {cfg.baseline.enabled}")
    logger.info(f"Output dir   : {cfg.output_dir}")
    if output_paths:
        logger.info(output_paths)
    logger.info(f"Log file     : {log_file}")
