"""
Narrative Generation Data Models

Defines data structures for narrative generation including sections,
contexts, and configuration for adaptive narrative generation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExpertiseLevel(str, Enum):
    """User expertise level for adaptive narrative generation"""

    BEGINNER = "beginner"  # Simple language, basic concepts
    INTERMEDIATE = "intermediate"  # Technical terms with explanations
    ADVANCED = "advanced"  # Professional terminology
    QUANT = "quant"  # Mathematical formulations


class Language(str, Enum):
    """Supported languages for narrative generation"""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    JAPANESE = "ja"
    CHINESE = "zh"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    FARSI = "fa"


class NarrativeType(str, Enum):
    """Types of narrative sections"""

    MARKET_CONTEXT = "market_context"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    RISK = "risk"
    SUMMARY = "summary"
    INSIGHTS = "insights"


class NarrativeSection(BaseModel):
    """
    Individual section of a narrative

    Represents a specific aspect of the analysis (technical, fundamental, etc.)
    with content, metadata, and confidence scoring.
    """

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=10, max_length=5000)
    section_type: NarrativeType
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    word_count: int = Field(0, ge=0)
    readability_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validate content meets length requirements"""
        if len(v) < 10:
            raise ValueError("Content must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Content must not exceed 5000 characters")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Calculate word count after initialization"""
        if self.word_count == 0:
            self.word_count = len(self.content.split())


class Narrative(BaseModel):
    """
    Complete narrative analysis

    Combines multiple narrative sections with summary, insights,
    and compliance information.
    """

    summary: str = Field(..., min_length=50, max_length=2000)
    sections: List[NarrativeSection] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    disclaimer: str = Field(..., min_length=10)
    language: Language = Language.ENGLISH
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    total_word_count: int = Field(0, ge=0)
    generation_time_ms: Optional[float] = Field(None, ge=0.0)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("key_insights")
    @classmethod
    def validate_insights(cls, v: List[str]) -> List[str]:
        """Validate insights are non-empty"""
        return [insight.strip() for insight in v if insight.strip()]

    @field_validator("risk_factors")
    @classmethod
    def validate_risk_factors(cls, v: List[str]) -> List[str]:
        """Validate risk factors are non-empty"""
        return [factor.strip() for factor in v if factor.strip()]

    def model_post_init(self, __context: Any) -> None:
        """Calculate total word count after initialization"""
        if self.total_word_count == 0:
            self.total_word_count = (
                len(self.summary.split())
                + sum(section.word_count for section in self.sections)
                + sum(len(insight.split()) for insight in self.key_insights)
            )

    def get_section(self, section_type: NarrativeType) -> Optional[NarrativeSection]:
        """Get a specific section by type"""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None

    def add_section(self, section: NarrativeSection) -> None:
        """Add a new section to the narrative"""
        self.sections.append(section)
        self.total_word_count += section.word_count


class NarrativePreferences(BaseModel):
    """User preferences for narrative generation"""

    language: Language = Language.ENGLISH
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    include_technical: bool = True
    include_fundamental: bool = True
    include_sentiment: bool = True
    include_risk: bool = True
    max_length_chars: int = Field(2000, ge=500, le=10000)
    min_confidence: float = Field(0.7, ge=0.0, le=1.0)
    include_disclaimers: bool = True
    focus_areas: List[str] = Field(default_factory=list)


class NarrativeContext(BaseModel):
    """
    Context for narrative generation

    Contains all the data and preferences needed to generate
    a comprehensive narrative analysis.
    """

    # Asset and market data
    asset_symbol: str
    asset_name: Optional[str] = None
    asset_type: str
    market: str = "US"

    # Analysis data
    price_data: Dict[str, Any] = Field(default_factory=dict)
    technical_data: Optional[Dict[str, Any]] = None
    fundamental_data: Optional[Dict[str, Any]] = None
    sentiment_data: Optional[Dict[str, Any]] = None
    risk_data: Optional[Dict[str, Any]] = None
    correlation_data: Optional[Dict[str, Any]] = None
    news_data: Optional[List[Dict[str, Any]]] = None

    # Generation preferences
    preferences: NarrativePreferences = Field(
        default_factory=NarrativePreferences
    )

    # Compliance and regional settings
    region: str = "US"
    include_disclaimers: bool = True

    # Metadata
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data_sources: List[str] = Field(default_factory=list)

    @field_validator("asset_symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize asset symbol"""
        return v.upper().strip()


class NarrativeQualityMetrics(BaseModel):
    """Metrics for evaluating narrative quality"""

    coherence_score: float = Field(..., ge=0.0, le=1.0)
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    accuracy_score: float = Field(..., ge=0.0, le=1.0)
    readability_score: float = Field(..., ge=0.0, le=100.0)
    compliance_score: float = Field(..., ge=0.0, le=1.0)
    overall_quality: float = Field(..., ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PromptTemplate(BaseModel):
    """Template for generating LLM prompts"""

    template_id: str
    template_type: NarrativeType
    expertise_level: ExpertiseLevel
    language: Language
    system_prompt: str
    user_prompt_template: str
    max_tokens: int = Field(1000, ge=100, le=4000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
