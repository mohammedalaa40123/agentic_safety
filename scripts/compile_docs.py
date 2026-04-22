import os
import yaml
import re

docs_dir = 'docs'
mkdocs_config = 'mkdocs.yml'
output_file = 'Agentic_Safety_Full_Docs.md'

class IgnoreTagsLoader(yaml.SafeLoader):
    pass

IgnoreTagsLoader.add_constructor(None, lambda loader, node: None)

with open(mkdocs_config, 'r') as f:
    config = yaml.load(f, Loader=IgnoreTagsLoader)

nav = config.get('nav', [])
all_mds = []

def extract_paths(nav_item):
    paths = []
    if isinstance(nav_item, str):
        paths.append(nav_item)
    elif isinstance(nav_item, dict):
        for key, value in nav_item.items():
            paths.extend(extract_paths(value))
    elif isinstance(nav_item, list):
        for item in nav_item:
            paths.extend(extract_paths(item))
    return paths

nav_paths = extract_paths(nav)

# Find all md files in docs
found_mds = []
for root, dirs, files in os.walk(docs_dir):
    for file in files:
        if file.endswith('.md'):
            rel_path = os.path.relpath(os.path.join(root, file), docs_dir)
            found_mds.append(rel_path)

# Combine following nav order
compiled_content = "# Agentic Safety Evaluation Framework - Compiled Documentation\n\n"
added_paths = set()

def fix_links_and_images(content, current_file_rel_path):
    # This is a basic adjustment for image paths and local links
    # Assuming images are in docs/assets and links are relative to current file
    
    current_dir = os.path.dirname(current_file_rel_path)
    
    # Adjust image paths: ![alt](path)
    def img_repl(match):
        alt = match.group(1)
        path = match.group(2)
        if not path.startswith('http') and not path.startswith('/'):
            abs_path = os.path.normpath(os.path.join('docs', current_dir, path))
            return f"![{alt}]({abs_path})"
        return match.group(0)
    
    content = re.sub(r'!\[(.*?)\]\((.*?)\)', img_repl, content)
    
    # We could also try to handle internal links [text](path.md)
    # but that's more complex since filenames might overlap in different dirs.
    # For now, let's just label sections clearly.
    
    return content

for path in nav_paths:
    full_path = os.path.join(docs_dir, path)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            content = f.read()
            compiled_content += f"\n---\n## Source: {path}\n\n"
            compiled_content += fix_links_and_images(content, path)
            compiled_content += "\n"
        added_paths.add(path)

# Add remaining mds that weren't in nav
remaining = set(found_mds) - added_paths
if remaining:
    compiled_content += "\n---\n# Additional Components & Operations (Unlisted in Nav)\n"
    for path in sorted(list(remaining)):
        full_path = os.path.join(docs_dir, path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
                compiled_content += f"\n---\n## Source: {path}\n\n"
                compiled_content += fix_links_and_images(content, path)
                compiled_content += "\n"

with open(output_file, 'w') as f:
    f.write(compiled_content)

print(f"Compiled documentation to {output_file}")
