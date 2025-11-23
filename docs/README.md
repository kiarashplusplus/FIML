# FIML Documentation

This directory contains the source files for the FIML documentation, built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

## Building the Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

### Local Development

Serve the documentation locally with live reload:

```bash
mkdocs serve
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### Build Static Site

Build the documentation to static HTML:

```bash
mkdocs build
```

The built site will be in the `site/` directory.

## Documentation Structure

```
docs/
├── index.md                    # Homepage
├── getting-started/            # Installation and quick start
│   ├── installation.md
│   ├── quickstart.md
│   └── configuration.md
├── user-guide/                 # User documentation
│   ├── overview.md
│   ├── mcp-tools.md
│   ├── websocket.md
│   └── fk-dsl.md
├── architecture/               # System architecture
│   ├── overview.md
│   ├── arbitration.md
│   ├── caching.md
│   ├── providers.md
│   └── agents.md
├── features/                   # Feature documentation
│   ├── watchdog.md
│   ├── mcp-narrative.md
│   ├── session-management.md
│   └── compliance.md
├── api/                        # API reference
│   ├── rest.md
│   ├── websocket.md
│   └── mcp.md
├── development/                # Developer guides
│   ├── contributing.md
│   ├── testing.md
│   ├── deployment.md
│   └── technical-debt.md
└── project/                    # Project documentation
    ├── roadmap.md
    ├── status.md
    ├── phase-reports.md
    └── changelog.md
```

## Contributing to Documentation

1. Edit markdown files in the `docs/` directory
2. Test locally with `mkdocs serve`
3. Commit and push changes
4. Documentation will be automatically deployed via GitHub Actions

## Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

**Live Documentation**: [https://kiarashplusplus.github.io/FIML/](https://kiarashplusplus.github.io/FIML/)

## MkDocs Configuration

Configuration is managed in `mkdocs.yml` at the repository root.

Key features:
- Material theme with dark mode
- Search functionality
- Code syntax highlighting
- Mermaid diagram support
- Git revision dates
- Minified HTML output

## Writing Documentation

### Markdown Basics

Use standard markdown syntax. The Material theme supports many extensions:

#### Admonitions

```markdown
!!! note "Optional Title"
    This is a note admonition.

!!! warning
    This is a warning.

!!! info
    This is an info box.
```

#### Code Blocks

```markdown
​```python
def example():
    return "Hello, World!"
​```
```

#### Tabs

```markdown
=== "Python"
    ​```python
    import fiml
    ​```

=== "JavaScript"
    ​```javascript
    const fiml = require('fiml');
    ​```
```

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)
