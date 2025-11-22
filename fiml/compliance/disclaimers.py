"""
Compliance Framework - Disclaimer Generation
"""

from enum import Enum
from typing import Dict, List, Union

from fiml.compliance.router import Region
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class AssetClass(str, Enum):
    """Asset classes for disclaimer customization"""
    EQUITY = "equity"
    CRYPTO = "crypto"
    DERIVATIVE = "derivative"
    FOREX = "forex"
    COMMODITY = "commodity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"


class DisclaimerGenerator:
    """
    Generate appropriate disclaimers based on region and asset type

    Ensures all financial information is properly disclaimed according
    to regional regulations.
    """

    def __init__(self):
        self.templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize disclaimer templates by region and asset class"""
        return {
            "US": {
                "general": (
                    "This information is provided for informational purposes only and does not "
                    "constitute financial advice, investment recommendation, or an offer or "
                    "solicitation to buy or sell any securities. Always conduct your own research "
                    "and consult with a qualified financial advisor before making investment decisions. "
                    "Past performance is not indicative of future results."
                ),
                "equity": (
                    "This stock information is provided for educational purposes only. "
                    "FIML is not a registered investment advisor or broker-dealer. "
                    "Securities trading involves substantial risk of loss. "
                    "This is not a recommendation to buy or sell any security."
                ),
                "crypto": (
                    "Cryptocurrency trading carries substantial risk and may not be suitable for all investors. "
                    "Cryptocurrencies are highly volatile and speculative. You may lose your entire investment. "
                    "FIML does not provide investment advice. "
                    "Consult with a financial professional before trading cryptocurrencies. "
                    "This is not an endorsement or recommendation of any cryptocurrency."
                ),
                "derivative": (
                    "Derivatives and leveraged products are complex instruments that carry high risk "
                    "and may not be suitable for all investors. You may lose more than your initial investment. "
                    "This information is educational only and does not constitute trading advice. "
                    "Seek professional guidance before trading derivatives."
                ),
            },
            "EU": {
                "general": (
                    "This material is provided for general information purposes only and does not "
                    "constitute investment advice or a recommendation within the meaning of MiFID II. "
                    "The information has not been prepared in accordance with legal requirements designed "
                    "to promote the independence of investment research. "
                    "We process your data in accordance with GDPR. "
                    "Past performance is not a reliable indicator of future performance."
                ),
                "equity": (
                    "This stock information is for educational purposes only and does not constitute "
                    "investment research or advice. The value of investments can go down as well as up. "
                    "You may get back less than you invested. This material has not been prepared in "
                    "accordance with legal requirements promoting investment research independence."
                ),
                "crypto": (
                    "WARNING: Crypto-assets are highly volatile and unregulated in some EU countries. "
                    "No EU investor protection. Tax may be due on profits. You may lose all your investment. "
                    "This is not investment advice. Crypto-assets are not suitable for retail investors."
                ),
                "derivative": (
                    "CFDs and leveraged derivative products are complex instruments with high risk of loss. "
                    "[X]% of retail investor accounts lose money when trading CFDs. "
                    "Consider whether you understand how these products work and whether you can afford "
                    "to take the high risk of losing your money. This is not investment advice."
                ),
            },
            "UK": {
                "general": (
                    "The information provided is for general information purposes only and does not "
                    "constitute financial advice or a financial promotion as defined by FCA regulations. "
                    "FIML is not authorized or regulated by the Financial Conduct Authority. "
                    "You should seek independent financial advice before making any investment decisions. "
                    "The value of investments can go down as well as up."
                ),
                "equity": (
                    "This is not investment advice or a recommendation to buy or sell securities. "
                    "The value of shares can go down as well as up. You may lose money. "
                    "Seek advice from an FCA-authorized financial adviser before investing."
                ),
                "crypto": (
                    "WARNING: Investments in cryptoassets are not regulated by the FCA. "
                    "You will not have access to the Financial Ombudsman Service or Financial Services "
                    "Compensation Scheme. You may lose all your money. The value of cryptoassets can go "
                    "down as well as up. This is not financial advice. Cryptoassets are high-risk investments."
                ),
                "derivative": (
                    "Spread betting and CFDs are complex instruments and come with a high risk of losing money. "
                    "Ensure you understand how these products work and whether you can afford to lose your money. "
                    "This is not investment advice. Seek FCA-authorized advice before trading."
                ),
            },
            "JP": {
                "general": (
                    "本情報は一般的な情報提供のみを目的としており、投資助言や金融商品の勧誘を構成するものではありません。"
                    "投資判断は、ご自身の責任において行ってください。"
                    "過去の実績は将来の成果を保証するものではありません。"
                    "\n\n"
                    "This information is for general informational purposes only and does not constitute "
                    "investment advice or solicitation. Investment decisions are your own responsibility. "
                    "Past performance does not guarantee future results."
                ),
                "equity": (
                    "株式投資にはリスクが伴います。投資元本を割り込む可能性があります。"
                    "投資判断は、ご自身の責任において行ってください。"
                    "\n\n"
                    "Stock investments carry risks. You may lose your principal. "
                    "Investment decisions are your own responsibility."
                ),
                "crypto": (
                    "暗号資産（仮想通貨）は価格変動が大きく、投資リスクが高い商品です。"
                    "投資元本を大きく割り込む可能性があります。十分ご注意ください。"
                    "\n\n"
                    "Crypto-assets are highly volatile and carry significant investment risk. "
                    "You may lose a substantial portion of your principal. Exercise caution."
                ),
            },
            "GLOBAL": {
                "general": (
                    "This information is provided for informational and educational purposes only. "
                    "It does not constitute financial, investment, or professional advice. "
                    "FIML is not responsible for any investment decisions you make based on this information. "
                    "Always conduct your own due diligence and consult with qualified professionals."
                ),
                "equity": (
                    "Stock market investments carry risk. The value of investments may fluctuate. "
                    "You may not get back the amount you invested. Past performance does not predict future results."
                ),
                "crypto": (
                    "Cryptocurrency trading is highly speculative and risky. "
                    "Cryptocurrencies are volatile and you may lose your entire investment. "
                    "Only invest what you can afford to lose."
                ),
            },
        }

    def generate(
        self,
        asset_class: AssetClass,
        region: Union[Region, str] = Region.US,
        include_general: bool = True,
    ) -> str:
        """
        Generate appropriate disclaimer

        Args:
            asset_class: Type of asset
            region: User's region
            include_general: Whether to include general disclaimer

        Returns:
            Formatted disclaimer text
        """
        logger.debug(f"Generating disclaimer for {asset_class} in {region}")

        disclaimers = []

        # Get region-specific templates
        region_value = region.value if isinstance(region, Region) else region
        region_templates = self.templates.get(region_value, self.templates["GLOBAL"])

        # Add general disclaimer
        if include_general:
            general = region_templates.get("general", self.templates["GLOBAL"]["general"])
            disclaimers.append(general)

        # Add asset-specific disclaimer
        asset_specific = region_templates.get(
            asset_class.value,
            self.templates["GLOBAL"].get(asset_class.value, "")
        )

        if asset_specific:
            disclaimers.append(asset_specific)

        # Combine disclaimers
        return "\n\n".join(disclaimers)

    # Alias for backward compatibility
    def generate_disclaimer(
        self,
        asset_class: AssetClass,
        region: Region = Region.US,
        include_general: bool = True,
        language: str = "en",
    ) -> str:
        """Alias for generate() method"""
        return self.generate(asset_class, region, include_general)

    def generate_multi_asset(
        self,
        asset_classes: List[AssetClass],
        region: Region = Region.US,
    ) -> str:
        """
        Generate disclaimer for multiple asset classes

        Args:
            asset_classes: List of asset types in response
            region: User's region

        Returns:
            Combined disclaimer text
        """
        disclaimers = []

        # Always include general disclaimer
        region_templates = self.templates.get(region.value, self.templates["GLOBAL"])
        general = region_templates.get("general", self.templates["GLOBAL"]["general"])
        disclaimers.append(general)

        # Add specific disclaimers for each asset class
        for asset_class in set(asset_classes):  # Remove duplicates
            asset_specific = region_templates.get(
                asset_class.value,
                self.templates["GLOBAL"].get(asset_class.value, "")
            )
            if asset_specific and asset_specific not in disclaimers:
                disclaimers.append(asset_specific)

        return "\n\n".join(disclaimers)

    def get_risk_warning(
        self,
        asset_class: AssetClass,
        region: Region = Region.US,
    ) -> str:
        """
        Get a short risk warning (for inline use)

        Args:
            asset_class: Type of asset
            region: User's region

        Returns:
            Brief risk warning
        """
        warnings = {
            AssetClass.EQUITY: "Investments can go down as well as up. You may lose money.",
            AssetClass.CRYPTO: "⚠️ High risk: Cryptocurrencies are extremely volatile. You may lose everything.",
            AssetClass.DERIVATIVE: "⚠️ High risk: Leveraged products can result in losses exceeding your investment.",
            AssetClass.FOREX: "⚠️ Forex trading carries substantial risk of loss.",
            AssetClass.COMMODITY: "Commodity investments are volatile and may result in losses.",
        }

        return warnings.get(asset_class, "Investment involves risk.")

    def get_compliance_footer(self, region: Region = Region.US) -> str:
        """
        Get compliance footer for display at bottom of all responses

        Args:
            region: User's region

        Returns:
            Compliance footer text
        """
        footers = {
            "US": (
                "FIML is not a registered investment advisor, broker-dealer, or financial planner. "
                "We provide information, not advice."
            ),
            "EU": (
                "FIML does not provide regulated investment services under MiFID II."
            ),
            "UK": (
                "FIML is not authorized or regulated by the Financial Conduct Authority."
            ),
            "JP": (
                "FIMLは金融商品取引業者ではありません。"
                "FIML is not a licensed financial instruments business operator."
            ),
            "GLOBAL": (
                "FIML provides financial data and information only, not personalized advice."
            ),
        }

        return footers.get(region.value, footers["GLOBAL"])


# Global disclaimer generator instance
disclaimer_generator = DisclaimerGenerator()
