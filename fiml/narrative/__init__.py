"""
Narrative Generation Module

Provides comprehensive narrative generation from financial analysis data
with multi-language support and adaptive expertise levels.
"""

from fiml.narrative.batch import BatchNarrativeGenerator
from fiml.narrative.cache import NarrativeCache, narrative_cache
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    Language,
    Narrative,
    NarrativeContext,
    NarrativePreferences,
    NarrativeQualityMetrics,
    NarrativeSection,
    NarrativeType,
)
from fiml.narrative.prompts import PromptTemplateLibrary, prompt_library
from fiml.narrative.templates import TemplateLibrary, template_library
from fiml.narrative.validator import NarrativeValidator, narrative_validator

__all__ = [
    # Generator
    "NarrativeGenerator",
    # Models
    "Narrative",
    "NarrativeSection",
    "NarrativeContext",
    "NarrativePreferences",
    "NarrativeQualityMetrics",
    "NarrativeType",
    "ExpertiseLevel",
    "Language",
    # Prompts
    "PromptTemplateLibrary",
    "prompt_library",
    # Templates
    "TemplateLibrary",
    "template_library",
    # Validator
    "NarrativeValidator",
    "narrative_validator",
    # Cache
    "NarrativeCache",
    "narrative_cache",
    # Batch
    "BatchNarrativeGenerator",
]
