# Contributing to FIML

Thank you for your interest in contributing to FIML (Financial Intelligence Meta-Layer)! 

## Development Setup

1. **Fork and clone the repository**
```bash
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**
```bash
make dev
```

4. **Start development services**
```bash
make up
```

## Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking
- **isort** for import sorting

Format your code before committing:
```bash
make format
```

Run linters:
```bash
make lint
```

## Testing

Run the test suite:
```bash
make test
```

Write tests for all new features and bug fixes.

## Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes
3. Add/update tests
4. Run `make format` and `make lint`
5. Ensure all tests pass
6. Update documentation as needed
7. Submit a pull request

## Commit Message Guidelines

Follow conventional commits:
```
feat: add new FK-DSL operator
fix: resolve cache invalidation bug
docs: update API documentation
test: add tests for arbitration engine
refactor: simplify provider registry
```

## Adding New Providers

1. Create a new file in `fiml/providers/`
2. Inherit from `BaseProvider`
3. Implement all abstract methods
4. Add configuration in `.env.example`
5. Register in `provider_registry`
6. Add tests

## Code Review

All pull requests require:
- Passing CI/CD checks
- Code review from at least one maintainer
- Up-to-date documentation

## Questions?

Open an issue or join our Discord community!
