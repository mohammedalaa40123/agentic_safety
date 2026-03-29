import sys

with open("run.py", "r") as f:
    orig = f.read()

replacement = """
    if mode == "agentic":
        logger.info("Building agentic-only target model (no hybrid_jailbreak)...")
        target_lm = build_agentic_target(cfg)
    else:
        logger.info("Loading attack and target models via HF (bypassing legacy conversers)...")
        
        # Load Attack model directly using local API
        attack_tgt = cfg.get("attack_model", "qwen25-7b")
        attack_lm = HFTarget(attack_tgt)
        
        # Load Target model directly using local API
        target_tgt = cfg.get("target_model", "qwen25-7b")
        target_lm = HFTarget(target_tgt)
        
        args = build_args_namespace(cfg)
        
        # We can either use a separate Judge model, or spoof it. Let's spoof it for a sec to verify the loop runs
        class SimpleJudge:
            def __init__(self, model):
                self.model = model
            def get_response(self, prompts):
                res = self.model.get_response(prompts)
                return res
        
        judge_lm = SimpleJudge(HFTarget(cfg.get("judge_model", "qwen25-7b")))

        logger.info("Models loaded successfully!")
"""

start_str = "    if mode == \"agentic\":\n        logger.info(\"Building agentic-only target model (no hybrid_jailbreak)...\")\n        target_lm = build_agentic_target(cfg)\n    else:\n        _ensure_hybrid_path()\n        from conversers import load_attack_and_target_models  # type: ignore\n        from judges import load_judge  # type: ignore\n\n        args = build_args_namespace(cfg)\n        logger.info(\"Loading attack and target models...\")\n        attack_lm, target_lm = load_attack_and_target_models(args)\n        \n        existing_model = None\n        if args.judge_model == args.target_model:\n            existing_model = target_lm\n        elif args.judge_model == args.attack_model:\n            existing_model = attack_lm\n            \n        logger.info(\"Loading judge model...\")\n        judge_lm = load_judge(args, existing_model)"


if start_str in orig:
    new_content = orig.replace(start_str, replacement.strip())
    with open("run.py", "w") as f:
        f.write(new_content)
    print("Patched run.py to bypass hybrid_jailbreak entirely!")
else:
    print("Could not find the block to replace.")

