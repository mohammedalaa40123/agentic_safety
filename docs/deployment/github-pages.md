# GitHub Pages Deployment

This repository includes a GitHub Actions workflow at `.github/workflows/docs.yml` that builds and deploys the MkDocs site automatically.

## Automated Deployment via GitHub Actions

On push to `main` or `master`, or on manual workflow dispatch:

1. Checks out the repository
2. Sets up Python 3.10
3. Installs docs requirements (`requirements-docs.txt`)
4. Runs `mkdocs build --strict` (fails build if any warnings found)
5. Uploads the generated `site/` artifact
6. Deploys via GitHub Pages Actions

**Live site**: https://mohammedalaa40123.github.io/agentic_safety/

## Local Workflow

Build and validate locally before pushing:

```bash
# Install docs dependencies
pip install -r requirements-docs.txt

# Strict build — catches broken links and missing pages
mkdocs build --strict

# Preview locally with hot-reload
mkdocs serve
```

## Manual Deploy from Local

Deploy to `gh-pages` branch directly (without CI):

```bash
mkdocs gh-deploy --clean
```

## Adding New Pages

When adding pages:

1. Create the `.md` file under `docs/`
2. Add an entry to `nav:` in `mkdocs.yml`
3. Run `mkdocs build --strict` to verify no broken references
4. Commit both the markdown file and the updated `mkdocs.yml`

!!! tip "Chart assets"
    Chart PNGs in `docs/assets/charts/` are committed to the repository and served directly. To update them, run `python scripts/gen_benchmark_charts.py` and commit the outputs.

## Configuration Notes

- `site_url` in `mkdocs.yml` must match the GitHub Pages URL exactly.
- GitHub Pages settings must be configured to use GitHub Actions (not the legacy `gh-pages` branch deploy method).
- `site_dir: site` is excluded from version control via `.gitignore`.
