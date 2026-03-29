import sys

with open("run.py", "r") as f:
    orig = f.read()

replacement = """    loop = None
    if mode != "agentic":
        from attacks.pair import PairAttackLoop
        class DummyConfig:
            n_iterations = cfg.get("n_iterations", 5)
        
        loop = PairAttackLoop(
            config=DummyConfig(),
            attack_lm=attack_lm,
            target_lm=target_lm,
            judge_lm=judge_lm,
            sandbox_builder_fn=lambda: build_sandbox_components(cfg)
        )"""

start_str = "    loop = None\n    if mode != \"agentic\":\n        from attacks.hybrid_loop import HybridAttackLoop, HybridConfig"
end_str = "hf_tools=hf_tools,\n        )"
start_idx = orig.find(start_str)
end_idx = orig.find(end_str) + len(end_str)

if start_idx != -1 and orig.find(end_str) != -1:
    new_content = orig[:start_idx] + replacement + orig[end_idx:]
    with open("run.py", "w") as f:
        f.write(new_content)
    print("Patched run.py.")
else:
    print("Could not find the block to replace.")
