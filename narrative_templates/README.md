# Narrative Templates

This directory contains template files for generating financial narratives across different languages.

## Template Types

### price_movement.txt
Market price movement analysis template.

### volume_analysis.txt
Trading volume analysis template.

### technical_summary.txt
Technical indicators summary template.

### fundamental_summary.txt
Fundamental analysis summary template.

### risk_assessment.txt
Risk profile assessment template.

## Languages Supported

- English (EN)
- Spanish (ES)
- French (FR)
- Japanese (JA)
- Chinese (ZH)

## Usage

Templates are loaded and rendered by the `TemplateLibrary` class in `fiml/narrative/templates.py`.

Example:
```python
from fiml.narrative.templates import template_library
from fiml.narrative.models import Language

narrative = template_library.render_template(
    "price_movement",
    Language.ENGLISH,
    {"symbol": "AAPL", "price": 175.50, "change_pct": 2.48}
)
```

## Template Variables

Each template type supports specific variables. See the template library documentation for details.

## Disclaimer

All templates include financial disclaimers as required by compliance.
