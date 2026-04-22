# agentic_safety — Agentic LLM Safety Evaluation Framework
# Extends hybrid GCG+PAIR jailbreaking to autonomous agent settings
#
# Architecture:
#   attacks/     — Attack modules (prompt fusion, crescendo, hybrid loop)
#   defenses/    — Defense wrappers (JBShield, Gradient Cuff, Progent, StepShield)
#   tools/       — Agentic tool sandbox (file I/O, code exec, web browse, network)
#   metrics/     — Metric collectors (MIR, TIR, DBR, QTJ)
#   configs/     — YAML configuration files

__version__ = "0.1.0"
