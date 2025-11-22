"""
Compliance Framework - Regional Compliance Routing
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel

from fiml.core.config import settings
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class Region(str, Enum):
    """Supported regions with different regulatory requirements"""
    US = "US"  # United States (SEC, FINRA)
    EU = "EU"  # European Union (MiFID II, ESMA)
    UK = "UK"  # United Kingdom (FCA)
    JP = "JP"  # Japan (JFSA)
    AU = "AU"  # Australia (ASIC)
    CA = "CA"  # Canada (CSA)
    SG = "SG"  # Singapore (MAS)
    HK = "HK"  # Hong Kong (SFC)
    GLOBAL = "GLOBAL"  # Default/International


class ComplianceLevel(str, Enum):
    """Compliance strictness levels"""
    STRICT = "strict"  # Full compliance enforcement
    MODERATE = "moderate"  # Balanced approach
    PERMISSIVE = "permissive"  # Minimal restrictions


class ComplianceRule(BaseModel):
    """Individual compliance rule"""
    rule_id: str
    region: Region
    rule_type: str  # "restriction", "warning", "disclosure"
    description: str
    enabled: bool = True
    severity: str = "medium"  # "low", "medium", "high", "critical"


class ComplianceCheck(BaseModel):
    """Result of a compliance check"""
    passed: bool
    region: Region
    rules_applied: List[str]
    warnings: List[str] = []
    restrictions: List[str] = []
    required_disclaimers: List[str] = []
    metadata: Dict = {}


class ComplianceRouter:
    """
    Routes requests through regional compliance checks

    Ensures all responses comply with regional financial regulations
    """

    def __init__(self, default_region: Region = Region.US):
        self.default_region = default_region
        self.rules: Dict[Region, List[ComplianceRule]] = self._initialize_rules()

    def _initialize_rules(self) -> Dict[Region, List[ComplianceRule]]:
        """Initialize compliance rules by region"""
        rules = {
            Region.US: [
                ComplianceRule(
                    rule_id="US-001",
                    region=Region.US,
                    rule_type="restriction",
                    description="Prohibit direct investment advice (SEC/FINRA)",
                    severity="critical"
                ),
                ComplianceRule(
                    rule_id="US-002",
                    region=Region.US,
                    rule_type="disclosure",
                    description="Require disclaimer for all financial information",
                    severity="high"
                ),
                ComplianceRule(
                    rule_id="US-003",
                    region=Region.US,
                    rule_type="warning",
                    description="Warn on high-risk assets (derivatives, crypto)",
                    severity="medium"
                ),
            ],
            Region.EU: [
                ComplianceRule(
                    rule_id="EU-001",
                    region=Region.EU,
                    rule_type="restriction",
                    description="Comply with MiFID II regulations",
                    severity="critical"
                ),
                ComplianceRule(
                    rule_id="EU-002",
                    region=Region.EU,
                    rule_type="disclosure",
                    description="GDPR data protection disclosure",
                    severity="high"
                ),
                ComplianceRule(
                    rule_id="EU-003",
                    region=Region.EU,
                    rule_type="disclosure",
                    description="Risk warnings for retail investors",
                    severity="high"
                ),
            ],
            Region.UK: [
                ComplianceRule(
                    rule_id="UK-001",
                    region=Region.UK,
                    rule_type="restriction",
                    description="FCA financial promotion rules",
                    severity="critical"
                ),
                ComplianceRule(
                    rule_id="UK-002",
                    region=Region.UK,
                    rule_type="warning",
                    description="Crypto asset warnings (FCA)",
                    severity="high"
                ),
            ],
            Region.JP: [
                ComplianceRule(
                    rule_id="JP-001",
                    region=Region.JP,
                    rule_type="restriction",
                    description="JFSA licensing requirements",
                    severity="critical"
                ),
                ComplianceRule(
                    rule_id="JP-002",
                    region=Region.JP,
                    rule_type="disclosure",
                    description="Japanese language disclosures required",
                    severity="medium"
                ),
            ],
            Region.GLOBAL: [
                ComplianceRule(
                    rule_id="GLOBAL-001",
                    region=Region.GLOBAL,
                    rule_type="disclosure",
                    description="General financial information disclaimer",
                    severity="medium"
                ),
            ],
        }

        return rules

    async def check_compliance(
        self,
        request_type: str,
        asset_type: str,
        region: Optional[Region] = None,
        user_query: Optional[str] = None,
    ) -> ComplianceCheck:
        """
        Check if request complies with regional regulations

        Args:
            request_type: Type of request (e.g., "price_query", "analysis", "recommendation")
            asset_type: Type of asset (e.g., "equity", "crypto", "derivative")
            region: User's region
            user_query: Original user query (for advice detection)

        Returns:
            ComplianceCheck with pass/fail and required actions
        """
        if region is None:
            region = self.default_region

        logger.info(f"Running compliance check for {request_type} in {region}")

        # Get rules for region
        regional_rules = self.rules.get(region, []) + self.rules.get(Region.GLOBAL, [])

        warnings = []
        restrictions = []
        required_disclaimers = []
        rules_applied = []
        passed = True

        # Check for investment advice
        if user_query and self._contains_advice_request(user_query):
            passed = False
            restrictions.append(
                "Request appears to seek investment advice. FIML provides information only, "
                "not personalized investment recommendations."
            )
            rules_applied.append(f"{region}-ADVICE-BLOCK")

        # Apply regional rules
        for rule in regional_rules:
            if not rule.enabled:
                continue

            rules_applied.append(rule.rule_id)

            if rule.rule_type == "restriction":
                if self._should_restrict(rule, asset_type, request_type):
                    restrictions.append(rule.description)
                    if rule.severity == "critical":
                        passed = False

            elif rule.rule_type == "warning":
                if self._should_warn(rule, asset_type, request_type):
                    warnings.append(rule.description)

            elif rule.rule_type == "disclosure":
                required_disclaimers.append(rule.rule_id)

        return ComplianceCheck(
            passed=passed,
            region=region,
            rules_applied=rules_applied,
            warnings=warnings,
            restrictions=restrictions,
            required_disclaimers=required_disclaimers,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_type": request_type,
                "asset_type": asset_type,
            }
        )

    def _contains_advice_request(self, query: str) -> bool:
        """Detect if query is requesting investment advice"""
        advice_keywords = [
            "should i buy",
            "should i sell",
            "should i invest",
            "is it a good time to",
            "what should i do",
            "recommend",
            "advise",
            "which one should i",
            "tell me what to",
            "is this a good investment",
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in advice_keywords)

    def _should_restrict(self, rule: ComplianceRule, asset_type: str, request_type: str) -> bool:
        """Determine if rule should trigger restriction"""
        # Crypto warnings in certain regions
        if "crypto" in rule.description.lower() and asset_type.lower() == "crypto":
            return True

        # Derivative warnings
        if "derivative" in rule.description.lower() and "derivative" in asset_type.lower():
            return True

        return False

    def _should_warn(self, rule: ComplianceRule, asset_type: str, request_type: str) -> bool:
        """Determine if rule should trigger warning"""
        # High-risk asset warnings
        if asset_type.lower() in ["crypto", "derivative", "option", "futures"]:
            if "risk" in rule.description.lower():
                return True

        return False

    def get_regional_restrictions(self, region: Region) -> List[str]:
        """Get all restrictions for a region"""
        rules = self.rules.get(region, [])
        return [
            rule.description
            for rule in rules
            if rule.rule_type == "restriction" and rule.enabled
        ]

    def is_region_supported(self, region: str) -> bool:
        """Check if region is supported"""
        try:
            Region(region)
            return True
        except ValueError:
            return False


# Global compliance router instance
compliance_router = ComplianceRouter(
    default_region=Region(settings.default_region)
)
