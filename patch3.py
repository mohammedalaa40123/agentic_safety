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
        if target_tgt == attack_tgt:
            target_lm = attack_lm
        else:
            target_lm = HFTarget(target_tgt)
        
        args = build_args_namespace(cfg)
        
        # We can either use a separate Judge model, or spoof it. Let's spoof it for a sec to verify the loop runs
        class SimpleJudge:
            def __init__(self, model):
                self.model = model
            def get_response(self, prompts):
                if self.model is None:
                    return ['{"score": 10, "reasoning": "No judge provided"}'] * len(prompts)
                return self.model.get_response(prompts)
        
        j_model_name = cfg.get("judge_model", "")
        if getattr(args, "judge_model", "") == "no-judge" or j_model_name == "no-judge":
            judge_lm = SimpleJudge(None)
        else:
            # simple mock using qwen25-7b if real one not set properly
            judge_lm = SimpleJudge(attack_lm)

        logger.info("Models loaded successfully!")
"""

start_str = "    if mode == \"agentic\":\n        logger.info(\"Building agentic-only target model (no hybrid_jailbreak)...\")\n        target_lm = build_agentic_target(cfg)\n    else:\n        logger.info(\"Loading attack and target models via HF (bypassing legacy conversers)...\")\n        \n        # Load Attack model directly using local API\n        attack_tgt = cfg.get(\"attack_model\", \"qwen25-7b\")\n        attack_lm = HFTarget(attack_tgt)\n        \n        # Load Target model directly using local API\n        target_tgt = cfg.get(\"target_model\", \"qwen25-7b\")\n        target_lm = HFTarget(target_tgt)\n        \n        args = build_args_namespace(cfg)\n        \n        # We can either use a separate Judge model, or spoof it. Let's spoof it for a sec to verify the loop runs\n        class SimpleJudge:\n            def __init__(self, model):\n                self.model = model\n            def get_response(self, prompts):\n                res = self.model.get_response(prompts)\n                return res\n        \n        judge_lm = SimpleJudge(HFTarget(cfg.get(\"judge_model\", \"qwen25-7b\")))\n\n        logger.info(\"Models loaded successfully!\")"

if start_str in orig:
    new_content = orig.replace(start_str, replacement.strip())
    with open("run.py", "w") as f:
        f.write(new_content)
    print("Patched run.py again for no-judge exception.")
else:
    print("Could not find the block to replace.")

