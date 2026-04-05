# Publishing to GitHub Pages

## Included workflow

A GitHub Actions workflow is provided at .github/workflows/docs.yml.

It will:

- Install documentation dependencies.
- Build docs with mkdocs build --strict.
- Upload the site artifact.
- Deploy to GitHub Pages on main/master pushes.

## Repository settings

In GitHub repository settings:

1. Open Settings -> Pages.
2. Set Source to GitHub Actions.
3. Ensure the default branch is main or master.

## Local verification

```bash
pip install -r requirements-docs.txt
mkdocs build --strict
mkdocs serve
```

## Updating documentation

- Edit docs/*.md pages.
- Update nav in mkdocs.yml when adding pages.
- Regenerate reference inventory pages when file layout changes.
