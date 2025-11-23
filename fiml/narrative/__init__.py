"""
Narrative Generation Module

Provides comprehensive narrative generation from financial analysis data
with multi-language support and adaptive expertise levels.
"""

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

__all__ = [
    "NarrativeGenerator",
    "Narrative",
    "NarrativeSection",
    "NarrativeContext",
    "NarrativePreferences",
    "NarrativeQualityMetrics",
    "NarrativeType",
    "ExpertiseLevel",
    "Language",
    "PromptTemplateLibrary",
    "prompt_library",
]
