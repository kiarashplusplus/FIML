# Contributing to FIML

Thank you for your interest in contributing to FIML (Financial Intelligence Meta-Layer)! This guide will help you get started.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/FIML.git
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

Or using pip directly:

```bash
pip install -e ".[dev]"
```

4. **Start development services**

```bash
make up
```

## Code Standards

### Code Style

We use the following tools to maintain code quality:

- **Black** - Code formatting
- **Ruff** - Fast Python linter
- **MyPy** - Static type checking
- **isort** - Import sorting

Format your code before committing:

```bash
make format
```

Run linters:

```bash
make lint
```

### Type Hints

All new code should include type hints:

```python
def process_data(symbol: str, market: str = "US") -> dict[str, Any]:
    """Process financial data for a symbol."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def fetch_price(symbol: str, provider: str) -> float:
    """Fetch current price for a symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        provider: Data provider name (e.g., "alpha_vantage")
        
    Returns:
        Current price as a float
        
    Raises:
        ProviderError: If provider fails to fetch data
    """
    ...
```

## Testing

### Running Tests

Run the full test suite:

```bash
make test
```

Run specific test file:

```bash
pytest tests/test_arbitration.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=fiml --cov-report=html
```

### Writing Tests

- Write tests for all new features
- Write tests for all bug fixes
- Aim for >80% code coverage
- Use descriptive test names
- Follow existing test patterns

Example test structure:

```python
import pytest
from fiml.providers import YahooFinanceProvider

class TestYahooFinanceProvider:
    """Tests for Yahoo Finance provider."""
    
    @pytest.fixture
    def provider(self):
        return YahooFinanceProvider()
    
    def test_fetch_price_success(self, provider):
        """Test successful price fetch."""
        price = provider.fetch_price("AAPL")
        assert price > 0
        assert isinstance(price, float)
    
    def test_fetch_price_invalid_symbol(self, provider):
        """Test error handling for invalid symbol."""
        with pytest.raises(ProviderError):
            provider.fetch_price("INVALID_SYMBOL_XYZ")
```

## Pull Request Process

### 1. Create a Feature Branch

Create a branch from `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions/improvements
- `refactor/` - Code refactoring

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code patterns
- Add/update tests
- Update documentation

### 3. Run Quality Checks

Before committing:

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test
```

### 4. Commit Your Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat: add new FK-DSL operator for moving averages
fix: resolve cache invalidation bug in Redis layer
docs: update API documentation for WebSocket endpoints
test: add tests for arbitration engine scoring
refactor: simplify provider registry initialization
perf: optimize database query performance
chore: update dependencies
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

### 6. PR Requirements

All pull requests must:

- ✅ Pass all CI/CD checks
- ✅ Include tests for new functionality
- ✅ Update documentation as needed
- ✅ Have a clear description of changes
- ✅ Get approval from at least one maintainer

## Contributing Guidelines

### Adding New Data Providers

To add a new data provider:

1. **Create provider class** in `fiml/providers/`

```python
from fiml.providers.base import BaseProvider

class NewProvider(BaseProvider):
    """Provider for New Data Source."""
    
    async def fetch_price(self, symbol: str) -> float:
        """Fetch current price."""
        ...
```

2. **Add configuration** in `.env.example`

```bash
NEW_PROVIDER_API_KEY=your_key_here
NEW_PROVIDER_RATE_LIMIT=60
```

3. **Register provider** in `fiml/providers/registry.py`

4. **Add tests** in `tests/providers/test_new_provider.py`

5. **Update documentation** in `docs/architecture/providers.md`

### Adding New MCP Tools

To add a new MCP tool:

1. **Define tool** in `fiml/mcp/tools/`
2. **Add schema** using Pydantic models
3. **Register tool** in tool registry
4. **Write tests**
5. **Update API documentation**

### Improving Documentation

Documentation improvements are always welcome!

- Fix typos and clarify explanations
- Add examples and use cases
- Improve API documentation
- Add diagrams and visualizations

To preview documentation locally:

```bash
mkdocs serve
```

Then open [http://localhost:8000](http://localhost:8000)

## Code Review Process

### Review Guidelines

When reviewing code:

- Be constructive and respectful
- Focus on code quality and correctness
- Suggest improvements, don't demand
- Acknowledge good work

### Response Time

We aim to:

- Acknowledge PRs within 48 hours
- Complete initial review within 1 week
- Merge approved PRs within 2 weeks

## Community

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and ideas
- **Discord** - Real-time chat and community support

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).

Be:
- Respectful and inclusive
- Patient and welcoming
- Collaborative and constructive

## Recognition

Contributors will be:

- Listed in `CONTRIBUTORS.md`
- Mentioned in release notes
- Acknowledged in documentation

## Questions?

- Check existing [GitHub Issues](https://github.com/kiarashplusplus/FIML/issues)
- Join our [Discord community](https://discord.gg/fiml)
- Read the [Documentation](https://kiarashplusplus.github.io/FIML/)

Thank you for contributing to FIML! 🚀
