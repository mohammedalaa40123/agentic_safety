import yaml
import os

base_template = {
    "experiment_name": "base",
    "description": "Base configuration",
    "mode": "agentic",
    "agentic_only": True,
    
    "attack_model": "qwen25-7b",
    "target_model": "qwen25-7b",
    "judge_model": "no-judge",
    
    "n_streams": 1,
    "n_iterations": 1,
    "keep_last_n": 2,
    "attack_max_n_tokens": 128,
    "target_max_n_tokens": 128,
    "judge_max_n_tokens": 8,
    "max_n_attack_attempts": 1,
    "judge_temperature": 0,
    "use_gcg": False,
    "early_stop": True,

    "fusion": {
        "strategy": "midpoint",
        "num_gcg_tokens": 1,
        "gcg_batch_size": 32,
        "gcg_topk": 16,
    },
    
    "crescendo": {
        "enabled": False
    },
    
    "sandbox": {
        "enabled": True,
        "max_steps": 3,
        "sandbox_root": "/tmp/agentic_sandbox",
        "tools": ["file_io", "code_exec", "web_browse", "network"],
        "code_timeout": 6,
        "web_sandbox": True,
        "net_sandbox": True
    },
    
    "defenses": {
        "enabled": False,
        "active": []
    },
    
    "goals_path": "data/agentic_scenarios_10_mixed.json",
    "output_dir": "results/agentic_experiments"
}

configs = [
    # 1. Baseline Qwen (No attacks, no defenses)
    {
        "name": "eval_qwen_baseline",
        "mods": {
            "experiment_name": "eval_qwen_baseline",
            "description": "Baseline evaluation of Qwen with 5/5 safe/unsafe data, no defenses or attacks."
        }
    },
    # 2. Baseline Llama3
    {
        "name": "eval_llama3_baseline",
        "mods": {
            "experiment_name": "eval_llama3_baseline",
            "description": "Baseline evaluation of Llama3.",
            "target_model": "llama3"
        }
    },
    # 3. PAIR Attack Qwen
    {
        "name": "eval_qwen_pair_attack",
        "mods": {
            "experiment_name": "eval_qwen_pair_attack",
            "description": "PAIR attack against Qwen target.",
            "agentic_only": False,
            "mode": "hybrid",
            "judge_model": "qwen25-7b"
        }
    },
    # 4. GCG Attack Qwen
    {
        "name": "eval_qwen_gcg_attack",
        "mods": {
            "experiment_name": "eval_qwen_gcg_attack",
            "description": "GCG attack against Qwen target.",
            "agentic_only": False,
            "mode": "hybrid",
            "use_gcg": True,
            "judge_model": "qwen25-7b"
        }
    },
    # 5. Crescendo Attack Qwen
    {
        "name": "eval_qwen_crescendo_attack",
        "mods": {
            "experiment_name": "eval_qwen_crescendo_attack",
            "description": "Crescendo multi-turn attack on Qwen.",
            "agentic_only": False,
            "mode": "hybrid",
            "crescendo": {"enabled": True},
            "judge_model": "qwen25-7b"
        }
    },
    # 6. Defense System Prompt Baseline 
    {
        "name": "eval_qwen_sysprompt",
        "mods": {
            "experiment_name": "eval_qwen_sysprompt",
            "description": "Qwen baseline with system prompt defense.",
            "defenses": {"enabled": True, "active": ["system_prompt"]}
        }
    },
    # 7. Defense LlamaGuard Baseline
    {
        "name": "eval_qwen_llamaguard",
        "mods": {
            "experiment_name": "eval_qwen_llamaguard",
            "description": "Qwen baseline with LlamaGuard IO defense.",
            "defenses": {"enabled": True, "active": ["llamaguard"]}
        }
    },
    # 8. Defense System Prompt + PAIR Attack
    {
        "name": "eval_qwen_sysprompt_pair",
        "mods": {
            "experiment_name": "eval_qwen_sysprompt_pair",
            "description": "PAIR attack against Qwen with System Prompt defense.",
            "agentic_only": False,
            "mode": "hybrid",
            "defenses": {"enabled": True, "active": ["system_prompt"]},
            "judge_model": "qwen25-7b"
        }
    },
    # 9. Judge Variation (Using Gemini Flash as judge) PAIR Attack
    {
        "name": "eval_qwen_pair_geminijudge",
        "mods": {
            "experiment_name": "eval_qwen_pair_geminijudge",
            "description": "PAIR attack using Gemini Flash to judge.",
            "agentic_only": False,
            "mode": "hybrid",
            "judge_model": "gemini-flash"
        }
    }
]

import copy

for c in configs:
    cfg = copy.deepcopy(base_template)
    cfg.update(c["mods"])
    # Write dict to yaml
    path = f"/depot/davisjam/data/mohamed/agentic_safety/configs/{c['name']}.yaml"
    with open(path, "w") as f:
        yaml.dump(cfg, f, sort_keys=False)

print("Generated yaml files!")

