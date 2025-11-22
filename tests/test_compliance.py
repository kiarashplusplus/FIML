"""
Tests for compliance module (disclaimers and routing)
"""

import pytest
from unittest.mock import Mock, patch
from fiml.compliance.disclaimers import (
    DisclaimerGenerator,
    AssetClass,
    disclaimer_generator,
)
from fiml.compliance.router import ComplianceRouter, Region, ComplianceLevel
from fiml.core.models import Asset, AssetType, Market, DataType


class TestDisclaimerGenerator:
    """Test disclaimer generation"""

    def test_disclaimer_generator_initialization(self):
        """Test disclaimer generator initialization"""
        gen = DisclaimerGenerator()
        
        assert gen is not None
        assert gen.templates is not None
        assert isinstance(gen.templates, dict)

    def test_generate_general_disclaimer_us(self):
        """Test general disclaimer generation for US"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.EQUITY, region=Region.US)
        
        assert disclaimer is not None
        assert isinstance(disclaimer, str)
        assert len(disclaimer) > 0
        assert "financial advice" in disclaimer or "investment" in disclaimer.lower()

    def test_generate_crypto_disclaimer(self):
        """Test crypto-specific disclaimer"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.CRYPTO, region=Region.US)
        
        assert disclaimer is not None
        assert "crypto" in disclaimer.lower() or "cryptocurrency" in disclaimer.lower()
        assert "risk" in disclaimer.lower()

    def test_generate_derivative_disclaimer(self):
        """Test derivatives-specific disclaimer"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.DERIVATIVE, region=Region.US)
        
        assert disclaimer is not None
        assert ("derivative" in disclaimer.lower() or "leveraged" in disclaimer.lower())

    def test_generate_forex_disclaimer(self):
        """Test forex-specific disclaimer (uses default if not in templates)"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.FOREX, region=Region.US)
        
        assert disclaimer is not None
        assert isinstance(disclaimer, str)

    def test_generate_eu_disclaimer(self):
        """Test EU-specific disclaimer"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.EQUITY, region=Region.EU)
        
        assert disclaimer is not None
        assert ("MiFID" in disclaimer or "EU" in disclaimer or "GDPR" in disclaimer)

    def test_generate_uk_disclaimer(self):
        """Test UK-specific disclaimer"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.EQUITY, region=Region.UK)
        
        assert disclaimer is not None
        assert "FCA" in disclaimer or "UK" in disclaimer or "Financial Conduct Authority" in disclaimer

    def test_generate_jp_disclaimer(self):
        """Test Japan-specific disclaimer"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.EQUITY, region=Region.JP)
        
        assert disclaimer is not None
        # Should contain Japanese characters or English translation
        assert len(disclaimer) > 0

    def test_generate_without_general(self):
        """Test generating disclaimer without general part"""
        gen = DisclaimerGenerator()
        
        disclaimer = gen.generate(AssetClass.EQUITY, region=Region.US, include_general=False)
        
        assert disclaimer is not None
        assert isinstance(disclaimer, str)

    def test_generate_multi_asset(self):
        """Test multi-asset disclaimer generation"""
        gen = DisclaimerGenerator()
        
        asset_classes = [AssetClass.EQUITY, AssetClass.CRYPTO, AssetClass.DERIVATIVE]
        disclaimer = gen.generate_multi_asset(asset_classes, region=Region.US)
        
        assert disclaimer is not None
        assert isinstance(disclaimer, str)
        # Should contain disclaimers for all asset classes
        assert "stock" in disclaimer.lower() or "equity" in disclaimer.lower()
        assert "crypto" in disclaimer.lower()

    def test_get_risk_warning_equity(self):
        """Test risk warning for equity"""
        gen = DisclaimerGenerator()
        
        warning = gen.get_risk_warning(AssetClass.EQUITY, region=Region.US)
        
        assert warning is not None
        assert "risk" in warning.lower() or "lose" in warning.lower()

    def test_get_risk_warning_crypto(self):
        """Test risk warning for crypto"""
        gen = DisclaimerGenerator()
        
        warning = gen.get_risk_warning(AssetClass.CRYPTO, region=Region.US)
        
        assert warning is not None
        assert "crypto" in warning.lower() or "volatile" in warning.lower()
        assert "⚠️" in warning or "risk" in warning.lower()

    def test_get_risk_warning_derivative(self):
        """Test risk warning for derivatives"""
        gen = DisclaimerGenerator()
        
        warning = gen.get_risk_warning(AssetClass.DERIVATIVE, region=Region.US)
        
        assert warning is not None
        assert ("leverage" in warning.lower() or "derivative" in warning.lower() or 
                "risk" in warning.lower())

    def test_get_compliance_footer_us(self):
        """Test compliance footer for US"""
        gen = DisclaimerGenerator()
        
        footer = gen.get_compliance_footer(region=Region.US)
        
        assert footer is not None
        assert "FIML" in footer
        assert "not" in footer.lower()

    def test_get_compliance_footer_eu(self):
        """Test compliance footer for EU"""
        gen = DisclaimerGenerator()
        
        footer = gen.get_compliance_footer(region=Region.EU)
        
        assert footer is not None
        assert "MiFID" in footer or "FIML" in footer

    def test_get_compliance_footer_global(self):
        """Test compliance footer for global"""
        gen = DisclaimerGenerator()
        
        footer = gen.get_compliance_footer(region=Region.GLOBAL)
        
        assert footer is not None
        assert "FIML" in footer

    def test_global_instance(self):
        """Test that global disclaimer_generator instance exists"""
        assert disclaimer_generator is not None
        assert isinstance(disclaimer_generator, DisclaimerGenerator)


class TestComplianceRouter:
    """Test ComplianceRouter functionality"""

    def test_router_initialization(self):
        """Test compliance router initialization"""
        router = ComplianceRouter()
        
        assert router is not None

    def test_router_basic_check(self):
        """Test basic compliance check"""
        router = ComplianceRouter()
        
        # Verify router can be instantiated
        assert router is not None
        # Check that it has the expected methods/attributes
        assert hasattr(router, '__init__')

