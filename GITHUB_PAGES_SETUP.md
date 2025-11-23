# Enabling GitHub Pages for FIML Documentation

Follow these steps to enable GitHub Pages and deploy the MkDocs documentation.

## Step 1: Enable GitHub Pages

1. Go to your repository: https://github.com/kiarashplusplus/FIML
2. Click on **Settings** (top menu)
3. Click on **Pages** (left sidebar)
4. Under "Build and deployment":
   - **Source**: Select "GitHub Actions"
5. Save the changes

## Step 2: Verify Workflow

The documentation workflow is already configured in `.github/workflows/docs.yml`.

It will automatically:
- Build documentation when changes are pushed to `main` branch
- Deploy to GitHub Pages
- Update the site at: https://kiarashplusplus.github.io/FIML/

## Step 3: Trigger First Deployment

The workflow will trigger automatically when:
- Changes to `docs/**` are pushed to `main`
- Changes to `mkdocs.yml` are pushed to `main`
- Manually triggered via Actions tab

To manually trigger:
1. Go to **Actions** tab
2. Select "Deploy Documentation" workflow
3. Click "Run workflow"
4. Select `main` branch
5. Click "Run workflow"

## Step 4: Verify Deployment

After the workflow completes (usually 2-3 minutes):

1. Check the Actions tab for successful deployment
2. Visit: https://kiarashplusplus.github.io/FIML/
3. Verify the documentation loads correctly

## Troubleshooting

### Workflow Fails

Check the Actions tab for error logs. Common issues:
- Missing permissions (already configured in workflow)
- Invalid markdown syntax (already validated)

### 404 Error

If you get a 404 error:
1. Wait a few minutes (GitHub Pages can take time to propagate)
2. Check that GitHub Pages is enabled
3. Verify the source is set to "GitHub Actions"

### Documentation Not Updating

1. Check that changes were pushed to `main` branch
2. Verify the workflow ran successfully in Actions tab
3. Clear browser cache and reload

## Local Testing

Always test documentation locally before pushing:

```bash
# Install dependencies
pip install -e ".[docs]"

# Serve locally
mkdocs serve

# Build and check for errors
mkdocs build --strict
```

## Next Steps

Once GitHub Pages is enabled:
1. All documentation updates will auto-deploy
2. Share the docs URL: https://kiarashplusplus.github.io/FIML/
3. Add the docs badge to README (optional)

## Documentation Badge (Optional)

Add this badge to your README to link to the docs:

```markdown
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://kiarashplusplus.github.io/FIML/)
```

## Support

If you encounter issues:
- Check [GitHub Pages Documentation](https://docs.github.com/en/pages)
- Review [MkDocs Documentation](https://www.mkdocs.org/)
- Open an issue in the repository
