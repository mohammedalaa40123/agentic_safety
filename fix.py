with open("attacks/pair.py", "r") as f:
    orig = f.read()

new_content = orig.replace('prompt = "\\n\n".join', 'prompt = "\\n".join')
new_content = new_content.replace('prompt = "\n".join', 'prompt = "\\n".join')
with open("attacks/pair.py", "w") as f:
    f.write(new_content)
