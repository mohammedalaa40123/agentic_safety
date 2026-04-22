# Publishing to GitHub Pages

This repository includes a GitHub Actions workflow at `.github/workflows/docs.yml` that builds and deploys the MkDocs site.

## How the workflow works

On pushes to `main` or `master`, or on manual dispatch, the workflow:

1. checks out the repository
2. sets up Python 3.10
3. installs docs requirements
4. builds the MkDocs site with `mkdocs build --strict`
5. uploads the generated `site/` artifact
6. deploys the site via GitHub Pages

## Local docs workflow

Build the docs locally:

```bash
pip install -r requirements-docs.txt
mkdocs build --strict
```

Preview locally:

```bash
mkdocs serve
```

## Deploy locally to gh-pages

If you want to deploy from your machine instead of via Actions:

```bash
mkdocs gh-deploy --clean
```

## Notes

- When adding new pages, update `mkdocs.yml` navigation.
- `site_url` is configured to the repository GitHub Pages address.
- If the site deployment fails, confirm that GitHub Pages settings are configured to use GitHub Actions.
