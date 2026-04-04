import os
import yaml
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    attack_model: str = "vicuna"
    target_model: str = "vicuna"
    judge_model: str = "llama-guard"
    attack_max_n_tokens: int = 500
    target_max_n_tokens: int = 150
    judge_max_n_tokens: int = 10
    attack_calls_per_minute: int = 0
    target_calls_per_minute: int = 0
    judge_calls_per_minute: int = 0


@dataclass
class SandboxConfig:
    enabled: bool = False
    sandbox_root: str = "/tmp/agentic_sandbox"
    tools: List[str] = field(default_factory=lambda: ["file_io", "code_exec", "web_browse", "network"])
    code_timeout: int = 10
    web_timeout: int = 10
    net_sandbox: bool = True
    web_sandbox: bool = True
    max_steps: int = 5


@dataclass
class AttackSpec:
    name: str
    enabled: bool = True
    stop_on_success: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DefenseConfig:
    enabled: bool = False
    active: List[str] = field(default_factory=list)
    jbshield: Dict[str, Any] = field(default_factory=dict)
    gradient_cuff: Dict[str, Any] = field(default_factory=dict)
    progent: Dict[str, Any] = field(default_factory=dict)
    stepshield: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineConfig:
    enabled: bool = False


@dataclass
class WandbConfig:
    enabled: bool = False
    project: str = "agentic-safety"
    entity: Optional[str] = None
    run_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    verbose: bool = True


@dataclass
class RunConfig:
    experiment_name: str = "agentic_run"
    description: str = ""
    mode: str = "attack"  # attack | baseline | agentic
    output_dir: str = "results"
    goals_path: str = "data/agentic_scenarios_smoke5.json"
    models: ModelConfig = field(default_factory=ModelConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    attacks: List[AttackSpec] = field(default_factory=lambda: [AttackSpec(name="pair")])
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    defenses: DefenseConfig = field(default_factory=DefenseConfig)
    wandb: WandbConfig = field(default_factory=WandbConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _coerce_attack_list(raw: Any) -> List[AttackSpec]:
    if not raw:
        return [AttackSpec(name="pair")]
    if isinstance(raw, dict):
        raw = [raw]
    plan: List[AttackSpec] = []
    for entry in raw:
        if isinstance(entry, str):
            plan.append(AttackSpec(name=entry))
            continue
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("type") or "pair"
        params = entry.get("params") if isinstance(entry.get("params"), dict) else {
            k: v for k, v in entry.items() if k not in {"name", "type", "enabled", "stop_on_success"}
        }
        plan.append(
            AttackSpec(
                name=name,
                enabled=entry.get("enabled", True),
                stop_on_success=entry.get("stop_on_success", True),
                params=params,
            )
        )
    if not any(a.enabled for a in plan):
        plan.append(AttackSpec(name="pair"))
    return plan


def load_config(path: str) -> RunConfig:
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    cfg = RunConfig()

    # --- Legacy top-level compatibility ------------------------------------
    legacy_models = data.get("models", {}) or {}
    for key in [
        "attack_model",
        "target_model",
        "judge_model",
        "attack_max_n_tokens",
        "target_max_n_tokens",
        "judge_max_n_tokens",
        "attack_calls_per_minute",
        "target_calls_per_minute",
        "judge_calls_per_minute",
    ]:
        if key in data and key not in legacy_models:
            legacy_models[key] = data[key]

    if not data.get("attacks") and data.get("n_iterations"):
        data["attacks"] = [{"name": "pair", "params": {"n_iterations": data["n_iterations"]}}]

    legacy_sandbox = data.get("sandbox", {}) or {}
    if data.get("use_sandbox") and not legacy_sandbox.get("enabled", False):
        legacy_sandbox["enabled"] = True
    for key in ["sandbox_root", "tools", "code_timeout", "web_timeout", "net_sandbox", "web_sandbox", "max_steps"]:
        if key in data and key not in legacy_sandbox:
            legacy_sandbox[key] = data[key]
    if legacy_sandbox:
        data["sandbox"] = legacy_sandbox

    legacy_defenses = data.get("defenses", {}) or {}
    if data.get("use_defenses") is not None:
        legacy_defenses["enabled"] = True
        if data.get("use_defenses"):
            legacy_defenses["active"] = data.get("use_defenses", [])
    if legacy_defenses:
        data["defenses"] = legacy_defenses

    if data.get("agentic_only") and not data.get("mode"):
        data["mode"] = "agentic"

    cfg.experiment_name = data.get("experiment_name", cfg.experiment_name)
    cfg.description = data.get("description", cfg.description)
    cfg.mode = data.get("mode", cfg.mode)
    cfg.output_dir = data.get("output_dir", cfg.output_dir)
    cfg.goals_path = data.get("goals_path", cfg.goals_path)

    models = legacy_models or data.get("models", {})
    cfg.models = ModelConfig(
        attack_model=models.get("attack_model", cfg.models.attack_model),
        target_model=models.get("target_model", cfg.models.target_model),
        judge_model=models.get("judge_model", cfg.models.judge_model),
        attack_max_n_tokens=models.get("attack_max_n_tokens", cfg.models.attack_max_n_tokens),
        target_max_n_tokens=models.get("target_max_n_tokens", cfg.models.target_max_n_tokens),
        judge_max_n_tokens=models.get("judge_max_n_tokens", cfg.models.judge_max_n_tokens),
        attack_calls_per_minute=models.get("attack_calls_per_minute", cfg.models.attack_calls_per_minute),
        target_calls_per_minute=models.get("target_calls_per_minute", cfg.models.target_calls_per_minute),
        judge_calls_per_minute=models.get("judge_calls_per_minute", cfg.models.judge_calls_per_minute),
    )

    sandbox = data.get("sandbox", {})
    cfg.sandbox = SandboxConfig(
        enabled=sandbox.get("enabled", cfg.sandbox.enabled),
        sandbox_root=sandbox.get("sandbox_root", cfg.sandbox.sandbox_root),
        tools=sandbox.get("tools", cfg.sandbox.tools),
        code_timeout=sandbox.get("code_timeout", cfg.sandbox.code_timeout),
        web_timeout=sandbox.get("web_timeout", cfg.sandbox.web_timeout),
        net_sandbox=sandbox.get("net_sandbox", cfg.sandbox.net_sandbox),
        web_sandbox=sandbox.get("web_sandbox", cfg.sandbox.web_sandbox),
        max_steps=sandbox.get("max_steps", cfg.sandbox.max_steps),
    )

    cfg.attacks = _coerce_attack_list(data.get("attacks"))
    cfg.baseline = BaselineConfig(enabled=data.get("baseline", {}).get("enabled", cfg.baseline.enabled))

    defenses = data.get("defenses", {})
    cfg.defenses = DefenseConfig(
        enabled=defenses.get("enabled", cfg.defenses.enabled),
        active=defenses.get("active", cfg.defenses.active),
        jbshield=defenses.get("jbshield", cfg.defenses.jbshield),
        gradient_cuff=defenses.get("gradient_cuff", cfg.defenses.gradient_cuff),
        progent=defenses.get("progent", cfg.defenses.progent),
        stepshield=defenses.get("stepshield", cfg.defenses.stepshield),
    )

    wandb = data.get("wandb", {})
    cfg.wandb = WandbConfig(
        enabled=wandb.get("enabled", cfg.wandb.enabled),
        project=wandb.get("project", cfg.wandb.project),
        entity=wandb.get("entity", cfg.wandb.entity),
        run_name=wandb.get("run_name", cfg.wandb.run_name),
        tags=wandb.get("tags", cfg.wandb.tags),
    )

    logging_cfg = data.get("logging", {})
    cfg.logging = LoggingConfig(verbose=logging_cfg.get("verbose", cfg.logging.verbose))

    return cfg


def apply_cli_overrides(cfg: RunConfig, args: Any) -> RunConfig:
    if getattr(args, "output_dir", None):
        cfg.output_dir = args.output_dir
    if getattr(args, "mode", None):
        cfg.mode = args.mode
    if getattr(args, "goals", None):
        cfg.goals_path = args.goals
    if getattr(args, "attack_model", None):
        cfg.models.attack_model = args.attack_model
    if getattr(args, "target_model", None):
        cfg.models.target_model = args.target_model
    if getattr(args, "judge_model", None):
        cfg.models.judge_model = args.judge_model
    if getattr(args, "verbose", False):
        cfg.logging.verbose = True
    if getattr(args, "use_sandbox", False):
        cfg.sandbox.enabled = True
    if getattr(args, "use_defenses", None) is not None:
        cfg.defenses.enabled = True
        cfg.defenses.active = args.use_defenses if args.use_defenses else cfg.defenses.active
    if getattr(args, "agentic_only", False):
        cfg.mode = "agentic"
    if getattr(args, "attack_plan", None):
        cfg.attacks = _coerce_attack_list(args.attack_plan)
    return cfg


def ensure_paths(cfg: RunConfig) -> RunConfig:
    cfg.output_dir = os.path.abspath(cfg.output_dir)
    return cfg
