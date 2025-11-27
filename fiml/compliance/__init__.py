"""
Compliance Framework for Financial Data

Provides compliance guardrails, disclaimer generation, and regional routing
to ensure all financial outputs meet regulatory requirements.

Key Components:
- ComplianceGuardrail: Final processing layer for compliance enforcement with multilingual support
- DisclaimerGenerator: Region and asset-specific disclaimer generation
- ComplianceRouter: Regional compliance routing and checks
- SupportedLanguage: Languages supported by the compliance guardrail
- MultilingualPatterns: Language-specific patterns for compliance detection
"""

from fiml.compliance.disclaimers import (
    AssetClass,
    DisclaimerGenerator,
    disclaimer_generator,
)
from fiml.compliance.guardrail import (
    ComplianceGuardrail,
    GuardrailAction,
    GuardrailResult,
    MultilingualPatterns,
    SupportedLanguage,
    compliance_guardrail,
)
from fiml.compliance.router import (
    ComplianceCheck,
    ComplianceLevel,
    ComplianceRouter,
    ComplianceRule,
    Region,
    compliance_router,
)

__all__ = [
    # Guardrail
    "ComplianceGuardrail",
    "GuardrailAction",
    "GuardrailResult",
    "compliance_guardrail",
    "SupportedLanguage",
    "MultilingualPatterns",
    # Disclaimers
    "AssetClass",
    "DisclaimerGenerator",
    "disclaimer_generator",
    # Router
    "ComplianceCheck",
    "ComplianceLevel",
    "ComplianceRouter",
    "ComplianceRule",
    "Region",
    "compliance_router",
]
