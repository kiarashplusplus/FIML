# Pre-Push Hook Documentation

## Overview

The FIML pre-push hook automatically runs quality checks before each `git push` to ensure code quality and prevent breaking changes from being pushed to remote branches.

## What It Does

The hook runs three checks in sequence:

1. **Ruff Linting** (`ruff check fiml/`)
   - Checks Python code for style issues and common errors
   - Must pass for push to proceed

2. **MyPy Type Checking** (`mypy fiml/`)
   - Validates type hints and type safety
   - Non-blocking (warnings only)

3. **Test Suite** (`pytest`)
   - Runs the full test suite with `--no-docker` flag
   - Must pass for push to proceed
   - Uses test environment configuration matching CI pipeline

## Installation

### Automatic Installation

```bash
./scripts/install-hooks.sh
```

For non-interactive/automated installation:
```bash
./scripts/install-hooks.sh --force
```

This script will:
- Check if you're in the FIML project root
- Backup any existing pre-push hook
- Copy the new hook to `.git/hooks/pre-push`
- Make it executable

### Manual Installation

```bash
cp scripts/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Usage

Once installed, the hook runs automatically on every `git push`:

```bash
git push origin feature/my-branch
```

Output example:
```
🔍 Running pre-push checks...

📝 Running ruff linter...
✅ Linting passed

🔍 Running mypy type checker...
✅ Type checking passed

🧪 Running test suite...
✅ Tests passed

✅ All pre-push checks passed!
🚀 Proceeding with push...
```

## Bypassing the Hook

**Not recommended**, but if you need to bypass the hook:

```bash
git push --no-verify
```

⚠️ **Warning**: Bypassing the hook may result in CI failures and rejected pull requests.

## Troubleshooting

### Hook Fails on Linting

Fix linting issues automatically:
```bash
ruff check --fix fiml/
```

Or run the full format process:
```bash
make format
```

### Hook Fails on Tests

Run tests locally to debug:
```bash
make test
```

Or run specific tests:
```bash
pytest tests/test_specific.py -v
```

### Hook is Not Running

Ensure the hook is executable:
```bash
chmod +x .git/hooks/pre-push
```

Verify the hook exists:
```bash
ls -l .git/hooks/pre-push
```

## Environment Variables

The hook sets the following environment variables for testing (matching CI):

```bash
FIML_ENV=test
REDIS_HOST=localhost
POSTGRES_HOST=localhost
POSTGRES_DB=fiml_test
POSTGRES_USER=fiml_test
POSTGRES_PASSWORD=fiml_test_password
AZURE_OPENAI_ENDPOINT=https://mock-azure-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=mock-api-key-for-testing
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## Benefits

✅ **Catch issues early** - Before code reaches CI/CD pipeline  
✅ **Save time** - No waiting for CI to fail  
✅ **Consistent quality** - Same checks as CI pipeline  
✅ **Better collaboration** - Less review back-and-forth  
✅ **CI/CD alignment** - Matches `.github/workflows/ci.yml`

## Related Files

- Hook template: `scripts/pre-push-hook.sh`
- Installation script: `scripts/install-hooks.sh`
- CI configuration: `.github/workflows/ci.yml`
- Test configuration: `pyproject.toml` (pytest section)
- Linting configuration: `pyproject.toml` (ruff section)

## Integration with CI/CD

The pre-push hook mimics the CI/CD pipeline defined in `.github/workflows/ci.yml`:

| Step | Pre-Push Hook | CI Pipeline |
|------|--------------|-------------|
| Linting | ✅ `ruff check` | ✅ `ruff check` |
| Type Check | ✅ `mypy` (non-blocking) | ✅ `mypy` (continue-on-error) |
| Tests | ✅ `pytest --no-docker` | ✅ `pytest --no-docker` |
| Coverage | ❌ Not checked | ✅ Coverage report |

## Customization

To customize the hook behavior, edit `scripts/pre-push-hook.sh` and run the installation script again:

```bash
vim scripts/pre-push-hook.sh
./scripts/install-hooks.sh
```

Common customizations:
- Change pytest flags (e.g., add `-x` to stop on first failure)
- Add additional checks (e.g., security scanning)
- Modify environment variables
- Change timeout settings
