with open("attacks/pair.py", "r") as f:
    orig = f.read()

replacement = """
            if hasattr(self.attack_lm, "batched_generate"):
                # Use batched_generate via common chat templates
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history])
                if hasattr(self.attack_lm, "model") and hasattr(self.attack_lm, "tokenizer"):
                    try:
                        prompt = self.attack_lm.tokenizer.apply_chat_template(conversation_history, tokenize=False, add_generation_prompt=True)
                    except:
                        pass
                res = self.attack_lm.batched_generate([prompt], max_n_tokens=1024, temperature=0.7)
                attack_response_text = res[0] if res else ""
            elif hasattr(self.attack_lm, "chat"):
                res = self.attack_lm.chat([conversation_history])
                attack_response_text = res[0] if res else ""
            else:
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history])
                res = self.attack_lm.get_response([prompt])
                attack_response_text = res[0] if res else ""
"""

target = "            attack_response_text = self.attack_lm.get_response(conversation_history)"

if target in orig:
    new_content = orig.replace(target, replacement)
    with open("attacks/pair.py", "w") as f:
        f.write(new_content)
    print("Patched attacks/pair.py ATTACK.")
else:
    print("Not found ATTACK")

target_judge = "            judge_response_text = self.judge_lm.get_response(judge_history)"

replacement_judge = """
            if hasattr(self.judge_lm, "batched_generate"):
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in judge_history])
                if hasattr(self.judge_lm, "tokenizer"):
                    try:
                        prompt = self.judge_lm.tokenizer.apply_chat_template(judge_history, tokenize=False, add_generation_prompt=True)
                    except:
                        pass
                res = self.judge_lm.batched_generate([prompt], max_n_tokens=512, temperature=0.0)
                judge_response_text = res[0] if res else ""
            elif hasattr(self.judge_lm, "chat"):
                res = self.judge_lm.chat([judge_history])
                judge_response_text = res[0] if res else ""
            else:
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in judge_history])
                res = getattr(self.judge_lm, "get_response", lambda x: [""])([prompt])
                judge_response_text = res[0] if res else ""
"""

if target_judge in orig:
    with open("attacks/pair.py", "r") as f:
        orig = f.read()
    new_content = orig.replace(target_judge, replacement_judge)
    with open("attacks/pair.py", "w") as f:
        f.write(new_content)
    print("Patched attacks/pair.py JUDGE.")
else:
    print("Not found JUDGE")

