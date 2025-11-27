"""
Compliance Guardrail Layer

A final processing layer that:
- Scans outputs for advice-like language
- Removes/replaces advice-like language
- Blocks prescriptive verbs
- Ensures the tone is descriptive only
- Adds disclaimers automatically
- Supports multiple languages (English, Spanish, French, German, Italian, Portuguese, Japanese, Chinese, Farsi)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from fiml.compliance.disclaimers import AssetClass, DisclaimerGenerator
from fiml.compliance.router import Region
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class GuardrailAction(str, Enum):
    """Actions that can be taken by the guardrail"""

    PASSED = "passed"  # Content is compliant
    MODIFIED = "modified"  # Content was modified to be compliant
    BLOCKED = "blocked"  # Content was blocked due to severe violations


class SupportedLanguage(str, Enum):
    """Languages supported by the compliance guardrail"""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    CHINESE = "zh"
    FARSI = "fa"
    AUTO = "auto"  # Auto-detect language


@dataclass
class GuardrailResult:
    """Result of guardrail processing"""

    action: GuardrailAction
    original_text: str
    processed_text: str
    modifications: List[str] = field(default_factory=list)
    violations_found: List[str] = field(default_factory=list)
    disclaimer_added: bool = False
    confidence: float = 1.0
    detected_language: Optional[str] = None

    @property
    def was_modified(self) -> bool:
        """
        Check if the text was modified by the guardrail.

        Returns True when the guardrail made compliance modifications to the
        original text, such as replacing advice language with descriptive
        alternatives or adding required disclaimers.
        """
        return self.action == GuardrailAction.MODIFIED

    @property
    def is_compliant(self) -> bool:
        """Check if the result is compliant (passed or modified)"""
        return self.action in (GuardrailAction.PASSED, GuardrailAction.MODIFIED)


class MultilingualPatterns:
    """
    Multilingual patterns for compliance detection and replacement.

    Provides prescriptive verbs, advice patterns, and replacements
    for multiple languages.
    """

    # Prescriptive verbs by language
    PRESCRIPTIVE_VERBS: Dict[str, List[str]] = {
        "en": [
            r"\bshould\b",
            r"\bmust\b",
            r"\bought to\b",
            r"\bneed to\b",
            r"\bhave to\b",
            r"\bbetter to\b",
            r"\badvise\b",
            r"\brecommend\b",
            r"\bsuggest\b",
            r"\burge\b",
            r"\bencourage\b",
        ],
        "es": [
            r"\bdebe\b",
            r"\bdebería\b",
            r"\bdeberías\b",
            r"\bhay que\b",
            r"\btiene que\b",
            r"\bnecesita\b",
            r"\brecomiendo\b",
            r"\brecomendamos\b",
            r"\bsugiero\b",
            r"\baconsejo\b",
            r"\bcompre\b",
            r"\bvenda\b",
            r"\binvierta\b",
        ],
        "fr": [
            r"\bdevrait\b",
            r"\bdevriez\b",
            r"\bdoit\b",
            r"\bdevez\b",
            r"\bfaut\b",
            r"\bconseille\b",
            r"\brecommande\b",
            r"\bsuggère\b",
            r"\bachetez\b",
            r"\bvendez\b",
            r"\binvestissez\b",
        ],
        "de": [
            r"\bsollte\b",
            r"\bsollten\b",
            r"\bmuss\b",
            r"\bmüssen\b",
            r"\bempfehle\b",
            r"\bempfehlen\b",
            r"\brate\b",
            r"\braten\b",
            r"\bkaufen Sie\b",
            r"\bverkaufen Sie\b",
        ],
        "it": [
            r"\bdovrebbe\b",
            r"\bdeve\b",
            r"\bbisogna\b",
            r"\bconsiglio\b",
            r"\braccomando\b",
            r"\bsuggerisco\b",
            r"\bcompri\b",
            r"\bvenda\b",
            r"\binvesta\b",
        ],
        "pt": [
            r"\bdeve\b",
            r"\bdeveria\b",
            r"\bprecisa\b",
            r"\brecomendo\b",
            r"\bsugiro\b",
            r"\baconselho\b",
            r"\bcompre\b",
            r"\bvenda\b",
            r"\binvista\b",
        ],
        "ja": [
            r"べき",
            r"なければならない",
            r"必要があります",
            r"お勧めします",
            r"推奨します",
            r"買うべき",
            r"売るべき",
            r"投資すべき",
            r"買ってください",
            r"売ってください",
        ],
        "zh": [
            r"应该",
            r"必须",
            r"需要",
            r"建议",
            r"推荐",
            r"买入",
            r"卖出",
            r"投资",
            r"购买",
            r"出售",
        ],
        "fa": [
            r"باید",
            r"بایست",
            r"لازم است",
            r"توصیه می‌کنم",
            r"پیشنهاد می‌کنم",
            r"بخرید",
            r"بفروشید",
            r"سرمایه‌گذاری کنید",
        ],
    }

    # Advice patterns by language (pattern, replacement)
    ADVICE_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "en": [
            # Direct advice patterns - improved for grammatical correctness
            # Handle variations with modifiers like "definitely", "certainly"
            (
                r"\byou should (definitely |certainly |absolutely |really )?(buy|sell|invest in|hold|trade)\b",
                "one may consider reviewing options to \\2",
            ),
            (
                r"\b(i |we )?(strongly |highly )?(recommend|suggest|advise)( that you| you)? (buy|sell|invest|hold|investing)\b",
                "the data shows factors related to \\5",
            ),
            (
                r"\b(buy|sell|invest in|trade) (now|immediately|today|asap)\b",
                "trading options are currently available",
            ),
            (
                r"\bthis is a (good|great|excellent|perfect) (time|opportunity) to (buy|sell|invest)\b",
                "current market conditions may be relevant for analysis",
            ),
            (
                r"\bdon'?t (buy|sell|invest in)\b",
                "caution may be warranted regarding",
            ),
            (
                r"\bavoid (buying|selling|investing in)\b",
                "careful consideration is suggested for",
            ),
            # Strong buy/sell recommendations
            (r"\bstrong (buy|sell)\b", "notable \\1 activity"),
            (r"\b(overweight|underweight)\b", "adjusted allocation"),
            # Prediction patterns - improved grammar
            (
                r"\bwill (definitely |certainly |surely |absolutely )?(go up|rise|fall|increase|decrease)\b",
                "has historically shown \\2 movement",
            ),
            (
                r"\b(is |are )?(guaranteed|certain|sure) to (rise|fall|increase|decrease|succeed|make)\b",
                "has shown historical patterns of \\3",
            ),
            (r"\bwill reach \$(\d+)", "is currently trading (historical highs around $\\1)"),
            (r"\bprice target\b", "price analysis level"),
            # Action imperative patterns
            (
                r"\b(buy|sell|get|grab|dump) (it|this|these|the stock|this stock)\b",
                "this asset is currently trading",
            ),
            (r"\bhold (it|this|these|the stock)\b", "the current position is noted"),
            (r"\bget in (now|before|while)\b", "trading activity is currently ongoing"),
            (r"\bget out (now|before|while)\b", "exit options are available"),
            (r"\bjump in\b", "entry options are available"),
            (r"\bpull out\b", "exit options are available"),
        ],
        "es": [
            (r"\bdebería(s)? (comprar|vender|invertir)\b", "considere revisar"),
            (
                r"\b(compre|venda|invierta) (ahora|inmediatamente|hoy)\b",
                "está disponible para operar",
            ),
            (
                r"\bes (buen|excelente|perfecto) momento para (comprar|vender)\b",
                "las condiciones actuales existen",
            ),
            (
                r"\bno (compre|venda|invierta)\b",
                "las condiciones actuales pueden requerir revisión",
            ),
            (
                r"\bevite (comprar|vender|invertir)\b",
                "las condiciones actuales pueden requerir revisión",
            ),
            (r"\brecomiendo (comprar|vender)\b", "los datos indican"),
            (r"\bva a (subir|bajar|aumentar|caer)\b", "ha mostrado movimiento"),
            (r"\bgarantizado\b", "históricamente ha mostrado"),
            (r"\bseguro que (sube|baja)\b", "históricamente ha mostrado"),
            (r"\bobjetivo de precio\b", "nivel de precio actual"),
            (r"\bcompra fuerte\b", "actividad notable"),
            (r"\bventa fuerte\b", "actividad notable"),
        ],
        "fr": [
            (r"\bvous devriez (acheter|vendre|investir)\b", "à considérer"),
            (
                r"\b(achetez|vendez|investissez) (maintenant|immédiatement|aujourd'hui)\b",
                "disponible pour le trading",
            ),
            (
                r"\bc'est (un bon|le bon|un excellent) moment pour (acheter|vendre)\b",
                "les conditions actuelles existent",
            ),
            (
                r"\bn'(achetez|vendez|investissez) pas\b",
                "les conditions actuelles peuvent nécessiter une révision",
            ),
            (
                r"\bévitez d'(acheter|vendre|investir)\b",
                "les conditions actuelles peuvent nécessiter une révision",
            ),
            (r"\bje (recommande|conseille) d'(acheter|vendre)\b", "les données indiquent"),
            (r"\bva (monter|baisser|augmenter|chuter)\b", "a montré un mouvement"),
            (r"\bgaranti\b", "a historiquement montré"),
            (r"\bcible de prix\b", "niveau de prix actuel"),
            (r"\bachat fort\b", "activité notable"),
            (r"\bvente forte\b", "activité notable"),
        ],
        "de": [
            (r"\bSie sollten (kaufen|verkaufen|investieren)\b", "zu überprüfen"),
            (
                r"\b(kaufen|verkaufen|investieren) Sie (jetzt|sofort|heute)\b",
                "ist derzeit handelbar",
            ),
            (
                r"\bist (ein guter|der richtige|ein ausgezeichneter) Zeitpunkt zum (Kaufen|Verkaufen)\b",
                "aktuelle Marktbedingungen existieren",
            ),
            (
                r"\b(kaufen|verkaufen|investieren) Sie nicht\b",
                "aktuelle Bedingungen erfordern möglicherweise Überprüfung",
            ),
            (
                r"\bvermeiden Sie (zu kaufen|zu verkaufen|zu investieren)\b",
                "aktuelle Bedingungen erfordern möglicherweise Überprüfung",
            ),
            (r"\bich empfehle (zu kaufen|zu verkaufen)\b", "Daten zeigen"),
            (r"\bwird (steigen|fallen|zunehmen|abnehmen)\b", "hat Bewegung gezeigt"),
            (r"\bgarantiert\b", "hat historisch gezeigt"),
            (r"\bKursziel\b", "aktuelles Kursniveau"),
            (r"\bstarker Kauf\b", "bemerkenswerte Aktivität"),
            (r"\bstarker Verkauf\b", "bemerkenswerte Aktivität"),
        ],
        "it": [
            (r"\bdovresti (comprare|vendere|investire)\b", "da considerare"),
            (r"\b(compra|vendi|investi) (ora|immediatamente|oggi)\b", "disponibile per il trading"),
            (
                r"\bè (un buon|il momento giusto|un ottimo) momento per (comprare|vendere)\b",
                "le condizioni attuali esistono",
            ),
            (
                r"\bnon (comprare|vendere|investire)\b",
                "le condizioni attuali potrebbero richiedere revisione",
            ),
            (
                r"\bevita di (comprare|vendere|investire)\b",
                "le condizioni attuali potrebbero richiedere revisione",
            ),
            (r"\b(consiglio|raccomando) di (comprare|vendere)\b", "i dati indicano"),
            (r"\b(salirà|scenderà|aumenterà|diminuirà)\b", "ha mostrato movimento"),
            (r"\bgarantito\b", "storicamente ha mostrato"),
            (r"\bobbiettivo di prezzo\b", "livello di prezzo attuale"),
            (r"\bforte acquisto\b", "attività notevole"),
            (r"\bforte vendita\b", "attività notevole"),
        ],
        "pt": [
            (r"\bvocê deveria (comprar|vender|investir)\b", "a considerar"),
            (
                r"\b(compre|venda|invista) (agora|imediatamente|hoje)\b",
                "disponível para negociação",
            ),
            (
                r"\bé (um bom|o momento certo|um excelente) momento para (comprar|vender)\b",
                "as condições atuais existem",
            ),
            (r"\bnão (compre|venda|invista)\b", "as condições atuais podem requerer revisão"),
            (r"\bevite (comprar|vender|investir)\b", "as condições atuais podem requerer revisão"),
            (r"\b(recomendo|sugiro) (comprar|vender)\b", "os dados indicam"),
            (r"\bvai (subir|cair|aumentar|diminuir)\b", "mostrou movimento"),
            (r"\bgarantido\b", "historicamente mostrou"),
            (r"\balvo de preço\b", "nível de preço atual"),
            (r"\bcompra forte\b", "atividade notável"),
            (r"\bvenda forte\b", "atividade notável"),
        ],
        "ja": [
            (r"買うべきです", "検討する価値があります"),
            (r"売るべきです", "検討する価値があります"),
            (r"投資すべきです", "検討する価値があります"),
            (r"今すぐ(買|売|投資)", "現在取引可能です"),
            (r"(買|売|投資)を(お勧め|推奨)します", "データが示しています"),
            (r"必ず(上がる|下がる|上昇|下落)", "動きを示しています"),
            (r"確実に(上がる|下がる)", "過去に示しています"),
            (r"目標株価", "現在の価格水準"),
            (r"強い買い", "注目すべき活動"),
            (r"強い売り", "注目すべき活動"),
        ],
        "zh": [
            (r"应该(买入|卖出|投资)", "值得考虑"),
            (r"(现在|立即|今天)(买入|卖出|投资)", "目前可交易"),
            (r"(建议|推荐)(买入|卖出)", "数据显示"),
            (r"不要(买入|卖出|投资)", "当前情况可能需要审查"),
            (r"避免(买入|卖出|投资)", "当前情况可能需要审查"),
            (r"一定会(上涨|下跌|增加|减少)", "已显示波动"),
            (r"保证(上涨|下跌)", "历史上显示"),
            (r"目标价", "当前价格水平"),
            (r"强烈买入", "值得关注的活动"),
            (r"强烈卖出", "值得关注的活动"),
        ],
        "fa": [
            (r"باید (بخرید|بفروشید|سرمایه‌گذاری کنید)", "قابل بررسی است"),
            (r"(الان|فوری|امروز) (بخرید|بفروشید)", "در حال حاضر قابل معامله است"),
            (r"(توصیه|پیشنهاد) می‌کنم (بخرید|بفروشید)", "داده‌ها نشان می‌دهد"),
            (r"(نخرید|نفروشید|سرمایه‌گذاری نکنید)", "شرایط فعلی ممکن است نیاز به بررسی داشته باشد"),
            (r"حتما (بالا|پایین) می‌رود", "حرکت نشان داده است"),
            (r"تضمین شده", "در گذشته نشان داده است"),
            (r"هدف قیمت", "سطح قیمت فعلی"),
            (r"خرید قوی", "فعالیت قابل توجه"),
            (r"فروش قوی", "فعالیت قابل توجه"),
        ],
    }

    # Opinion as fact patterns by language - improved for grammatical correctness
    OPINION_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "en": [
            (
                r"\bthis (stock|asset|investment) is (undervalued|overvalued)\b",
                "this \\1 has metrics that some analysts consider relevant",
            ),
            (
                r"\b(definitely|certainly|obviously|clearly) a (buy|sell|hold)\b",
                "currently showing \\2 activity",
            ),
            (r"\ba no-brainer\b", "an opportunity that warrants analysis"),
            (r"\bno-brainer\b", "opportunity that warrants analysis"),
            (r"\beasy money\b", "a trading opportunity"),
            (r"\b(you |one )?cannot lose\b", "all investments carry inherent risk"),
            (r"\brisk-free\b", "an option with associated risks"),
            (r"\ba risk-free\b", "an option with associated risks"),
            (r"\bsafe bet\b", "an opportunity requiring due diligence"),
            (r"\ba safe bet\b", "an opportunity requiring due diligence"),
            (r"\bguaranteed (returns?|profit|gains?)\b", "potential \\1 (not guaranteed)"),
            (
                r"\b(is |are )?guaranteed to (rise|fall|succeed)\b",
                "has historical patterns related to \\2",
            ),
            (r"\b(is |are )?sure to (rise|fall|make)\b", "has historical patterns related to \\2"),
        ],
        "es": [
            (r"\b(está|es) (infravalorado|sobrevalorado)\b", "tiene métricas actuales"),
            (
                r"\b(definitivamente|claramente|obviamente) (comprar|vender)\b",
                "actualmente cotizando",
            ),
            (r"\bdinero fácil\b", "oportunidad de trading presente"),
            (r"\bno puede perder\b", "el riesgo es inherente al trading"),
            (r"\bsin riesgo\b", "con riesgos asociados"),
        ],
        "fr": [
            (r"\b(est|sont) (sous-évalué|surévalué)\b", "a des métriques actuelles"),
            (
                r"\b(définitivement|clairement|évidemment) (acheter|vendre)\b",
                "actuellement en trading",
            ),
            (r"\bargent facile\b", "opportunité de trading présente"),
            (r"\bne peut pas perdre\b", "le risque est inhérent au trading"),
            (r"\bsans risque\b", "avec des risques associés"),
        ],
        "de": [
            (r"\b(ist|sind) (unterbewertet|überbewertet)\b", "hat aktuelle Kennzahlen"),
            (r"\b(definitiv|eindeutig|offensichtlich) (kaufen|verkaufen)\b", "derzeit handelbar"),
            (r"\bleichtes Geld\b", "Handelsmöglichkeit vorhanden"),
            (r"\bkann nicht verlieren\b", "Risiko ist dem Handel inhärent"),
            (r"\brisikofrei\b", "mit verbundenen Risiken"),
        ],
        "it": [
            (r"\b(è|sono) (sottovalutato|sopravvalutato)\b", "ha metriche attuali"),
            (
                r"\b(sicuramente|chiaramente|ovviamente) (comprare|vendere)\b",
                "attualmente in trading",
            ),
            (r"\bsoldi facili\b", "opportunità di trading presente"),
            (r"\bnon può perdere\b", "il rischio è inerente al trading"),
            (r"\bsenza rischio\b", "con rischi associati"),
        ],
        "pt": [
            (r"\b(está|é) (subvalorizado|sobrevalorizado)\b", "tem métricas atuais"),
            (
                r"\b(definitivamente|claramente|obviamente) (comprar|vender)\b",
                "atualmente negociando",
            ),
            (r"\bdinheiro fácil\b", "oportunidade de trading presente"),
            (r"\bnão pode perder\b", "o risco é inerente ao trading"),
            (r"\bsem risco\b", "com riscos associados"),
        ],
        "ja": [
            (r"(割安|割高)です", "現在の指標があります"),
            (r"絶対に(買い|売り)", "現在取引中"),
            (r"簡単にお金", "取引機会があります"),
            (r"損することはない", "リスクは取引に固有です"),
            (r"リスクなし", "関連するリスクがあります"),
        ],
        "zh": [
            (r"(被低估|被高估)", "有当前指标"),
            (r"绝对要(买|卖)", "目前正在交易"),
            (r"轻松赚钱", "存在交易机会"),
            (r"不会亏损", "风险是交易固有的"),
            (r"无风险", "存在相关风险"),
        ],
        "fa": [
            (r"(کم‌ارزش‌گذاری|بیش‌ارزش‌گذاری) شده", "دارای معیارهای فعلی است"),
            (r"قطعا باید (بخرید|بفروشید)", "در حال معامله است"),
            (r"پول آسان", "فرصت معاملاتی وجود دارد"),
            (r"نمی‌توانید ضرر کنید", "ریسک ذاتی معاملات است"),
            (r"بدون ریسک", "با ریسک‌های مرتبط"),
        ],
    }

    # Certainty patterns by language - improved for grammatical flow
    CERTAINTY_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "en": [
            (
                r"\bwill (increase|rise|go up|climb|surge)\b",
                "has historically shown \\1 patterns",
            ),
            (
                r"\bwill (decrease|fall|drop|decline|plunge)\b",
                "has historically shown \\1 patterns",
            ),
            (
                r"\b(is |are )?going to (increase|rise|go up)\b",
                "has shown recent upward movement",
            ),
            (
                r"\b(is |are )?going to (decrease|fall|drop)\b",
                "has shown recent downward movement",
            ),
            (
                r"\bexpect(?:ed|s)? to (reach|hit|exceed)\b",
                "has historically been known to \\1",
            ),
            (r"\blikely to (increase|rise|go up)\b", "has shown positive trend indicators"),
            (r"\blikely to (decrease|fall|drop)\b", "has shown negative trend indicators"),
            (r"\bpredicted to (rise|fall|reach|hit)\b", "has historical patterns of \\1"),
            (r"\bforecast(?:ed)? to (rise|fall|reach)\b", "has historical patterns of \\1"),
            (r"\bbound to (rise|fall|succeed|fail)\b", "has historical tendencies to \\1"),
        ],
        "es": [
            (r"\bva a (subir|aumentar|crecer)\b", "ha mostrado movimiento alcista"),
            (r"\bva a (bajar|caer|disminuir)\b", "ha mostrado movimiento bajista"),
            (r"\bse espera que (alcance|llegue|supere)\b", "históricamente ha alcanzado"),
            (r"\bprobablemente (suba|aumente)\b", "ha mostrado tendencias positivas"),
            (r"\bprobablemente (baje|caiga)\b", "ha mostrado tendencias negativas"),
            (r"\bse predice que\b", "ha mostrado patrones históricos de"),
        ],
        "fr": [
            (r"\bva (monter|augmenter|grimper)\b", "a montré un mouvement haussier"),
            (r"\bva (baisser|chuter|diminuer)\b", "a montré un mouvement baissier"),
            (r"\bon s'attend à (atteindre|dépasser)\b", "a historiquement atteint"),
            (r"\bdevrait (monter|augmenter)\b", "a montré des tendances positives"),
            (r"\bdevrait (baisser|chuter)\b", "a montré des tendances négatives"),
            (r"\bprévu pour\b", "a montré des modèles historiques de"),
        ],
        "de": [
            (r"\bwird (steigen|zunehmen|klettern)\b", "hat Aufwärtsbewegung gezeigt"),
            (r"\bwird (fallen|sinken|abnehmen)\b", "hat Abwärtsbewegung gezeigt"),
            (r"\bwird voraussichtlich (erreichen|übertreffen)\b", "hat historisch erreicht"),
            (r"\bwahrscheinlich (steigen|zunehmen)\b", "hat positive Trends gezeigt"),
            (r"\bwahrscheinlich (fallen|sinken)\b", "hat negative Trends gezeigt"),
            (r"\bprognostiziert\b", "hat historische Muster gezeigt von"),
        ],
        "it": [
            (r"\b(salirà|aumenterà|crescerà)\b", "ha mostrato movimento rialzista"),
            (r"\b(scenderà|calerà|diminuirà)\b", "ha mostrato movimento ribassista"),
            (r"\bsi prevede che (raggiunga|superi)\b", "storicamente ha raggiunto"),
            (r"\bprobabilmente (salirà|aumenterà)\b", "ha mostrato tendenze positive"),
            (r"\bprobabilmente (scenderà|calerà)\b", "ha mostrato tendenze negative"),
        ],
        "pt": [
            (r"\bvai (subir|aumentar|crescer)\b", "mostrou movimento de alta"),
            (r"\bvai (cair|diminuir|descer)\b", "mostrou movimento de baixa"),
            (r"\bespera-se que (alcance|atinja|supere)\b", "historicamente alcançou"),
            (r"\bprovavelmente (subirá|aumentará)\b", "mostrou tendências positivas"),
            (r"\bprovavelmente (cairá|diminuirá)\b", "mostrou tendências negativas"),
        ],
        "ja": [
            (r"(上がる|上昇する|増加する)でしょう", "上昇の動きを示しています"),
            (r"(下がる|下落する|減少する)でしょう", "下降の動きを示しています"),
            (r"(到達|達成)すると予想", "歴史的に到達しています"),
            (r"おそらく(上がる|上昇)", "ポジティブなトレンドを示しています"),
            (r"おそらく(下がる|下落)", "ネガティブなトレンドを示しています"),
        ],
        "zh": [
            (r"将会(上涨|增加|攀升)", "已显示上行走势"),
            (r"将会(下跌|减少|下降)", "已显示下行走势"),
            (r"预计将(达到|超过)", "历史上曾达到"),
            (r"可能会(上涨|增加)", "已显示积极趋势"),
            (r"可能会(下跌|减少)", "已显示消极趋势"),
        ],
        "fa": [
            (r"(افزایش|رشد|صعود) خواهد کرد", "حرکت صعودی نشان داده است"),
            (r"(کاهش|سقوط|نزول) خواهد کرد", "حرکت نزولی نشان داده است"),
            (r"انتظار می‌رود (برسد|تجاوز کند)", "در گذشته رسیده است"),
            (r"احتمالا (افزایش|رشد) می‌یابد", "روندهای مثبت نشان داده است"),
            (r"احتمالا (کاهش|سقوط) می‌کند", "روندهای منفی نشان داده است"),
        ],
    }

    # Required disclaimer phrases by language
    DISCLAIMER_PHRASES: Dict[str, List[str]] = {
        "en": [
            "not financial advice",
            "not investment advice",
            "informational purposes only",
            "educational purposes only",
            "data analysis only",
            "consult a financial advisor",
            "consult a qualified professional",
            "past performance",
        ],
        "es": [
            "no es asesoramiento financiero",
            "no es consejo de inversión",
            "solo con fines informativos",
            "solo con fines educativos",
            "solo análisis de datos",
            "consulte a un asesor financiero",
            "rendimiento pasado",
        ],
        "fr": [
            "n'est pas un conseil financier",
            "n'est pas un conseil d'investissement",
            "à des fins d'information uniquement",
            "à des fins éducatives uniquement",
            "analyse de données uniquement",
            "consultez un conseiller financier",
            "performance passée",
        ],
        "de": [
            "keine finanzberatung",
            "keine anlageberatung",
            "nur zu informationszwecken",
            "nur zu bildungszwecken",
            "nur datenanalyse",
            "konsultieren sie einen finanzberater",
            "vergangene leistung",
        ],
        "it": [
            "non è consulenza finanziaria",
            "non è consulenza sugli investimenti",
            "solo a scopo informativo",
            "solo a scopo educativo",
            "solo analisi dei dati",
            "consultare un consulente finanziario",
            "performance passata",
        ],
        "pt": [
            "não é aconselhamento financeiro",
            "não é aconselhamento de investimento",
            "apenas para fins informativos",
            "apenas para fins educacionais",
            "apenas análise de dados",
            "consulte um consultor financeiro",
            "desempenho passado",
        ],
        "ja": [
            "金融アドバイスではありません",
            "投資アドバイスではありません",
            "情報提供のみ",
            "教育目的のみ",
            "データ分析のみ",
            "ファイナンシャルアドバイザーに相談してください",
            "過去のパフォーマンス",
        ],
        "zh": [
            "不构成财务建议",
            "不构成投资建议",
            "仅供参考",
            "仅供教育目的",
            "仅供数据分析",
            "请咨询财务顾问",
            "过去的表现",
        ],
        "fa": [
            "مشاوره مالی نیست",
            "مشاوره سرمایه‌گذاری نیست",
            "فقط برای اهداف اطلاعاتی",
            "فقط برای اهداف آموزشی",
            "فقط تجزیه و تحلیل داده",
            "با یک مشاور مالی مشورت کنید",
            "عملکرد گذشته",
        ],
    }

    # Language detection indicators
    LANGUAGE_INDICATORS: Dict[str, List[str]] = {
        "es": ["está", "esto", "pero", "como", "para", "con", "que", "los", "las", "una", "del"],
        "fr": ["est", "cette", "mais", "comme", "pour", "avec", "que", "les", "une", "des", "dans"],
        "de": ["ist", "diese", "aber", "wie", "für", "mit", "dass", "die", "der", "das", "und"],
        "it": ["è", "questa", "ma", "come", "per", "con", "che", "gli", "una", "del", "nella"],
        "pt": ["está", "esta", "mas", "como", "para", "com", "que", "os", "as", "uma", "do"],
        "ja": ["は", "が", "を", "に", "で", "と", "も", "の", "です", "ます", "した"],
        "zh": ["的", "是", "在", "了", "和", "有", "这", "为", "与", "以", "但"],
        "fa": ["است", "این", "اما", "برای", "با", "که", "از", "را", "در", "به", "می"],
    }


class ComplianceGuardrail:
    """
    Compliance Guardrail Layer for financial outputs

    Ensures all outputs are descriptive only and do not contain
    investment advice, recommendations, or prescriptive language.
    Supports multiple languages for global compliance.

    Example usage:
        >>> guardrail = ComplianceGuardrail()
        >>> result = guardrail.process("You should buy AAPL stock now!")
        >>> print(result.processed_text)
        "AAPL stock is currently available for trading."
        >>> print(result.was_modified)
        True

        # With language specification
        >>> result = guardrail.process(
        ...     "Debería comprar AAPL ahora!",
        ...     language=SupportedLanguage.SPANISH
        ... )
    """

    # Configurable thresholds
    LANGUAGE_DETECTION_MIN_SCORE = (
        3  # Minimum language indicator matches to override English default
    )
    STRICT_MODE_MAX_VIOLATIONS = 5  # Maximum violations before blocking in strict mode

    def __init__(
        self,
        disclaimer_generator: Optional[DisclaimerGenerator] = None,
        strict_mode: bool = False,
        auto_add_disclaimer: bool = True,
        default_language: SupportedLanguage = SupportedLanguage.ENGLISH,
        language_detection_threshold: int = LANGUAGE_DETECTION_MIN_SCORE,
        strict_mode_violation_limit: int = STRICT_MODE_MAX_VIOLATIONS,
    ):
        """
        Initialize the Compliance Guardrail

        Args:
            disclaimer_generator: Generator for disclaimers (creates new if None)
            strict_mode: If True, blocks content with severe violations instead of modifying
            auto_add_disclaimer: If True, automatically adds disclaimers when missing
            default_language: Default language for processing (default: English)
            language_detection_threshold: Minimum score to detect non-English language (default: 3)
            strict_mode_violation_limit: Maximum violations before blocking in strict mode (default: 5)
        """
        self.disclaimer_generator = disclaimer_generator or DisclaimerGenerator()
        self.strict_mode = strict_mode
        self.auto_add_disclaimer = auto_add_disclaimer
        self.default_language = default_language
        self.language_detection_threshold = language_detection_threshold
        self.strict_mode_violation_limit = strict_mode_violation_limit

        # Cache for compiled patterns by language
        self._compiled_patterns_cache: Dict[str, Dict[str, List]] = {}

        logger.info(
            "Compliance guardrail initialized",
            strict_mode=strict_mode,
            auto_add_disclaimer=auto_add_disclaimer,
            default_language=default_language.value,
        )

    def _get_compiled_patterns(self, lang_code: str) -> Dict[str, List]:
        """
        Get compiled regex patterns for a specific language

        Args:
            lang_code: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            Dictionary of compiled patterns for the language
        """
        if lang_code in self._compiled_patterns_cache:
            return self._compiled_patterns_cache[lang_code]

        patterns = MultilingualPatterns

        # Get patterns for language, fallback to English if not available
        prescriptive = patterns.PRESCRIPTIVE_VERBS.get(
            lang_code, patterns.PRESCRIPTIVE_VERBS.get("en", [])
        )
        advice = patterns.ADVICE_PATTERNS.get(lang_code, patterns.ADVICE_PATTERNS.get("en", []))
        opinion = patterns.OPINION_PATTERNS.get(lang_code, patterns.OPINION_PATTERNS.get("en", []))
        certainty = patterns.CERTAINTY_PATTERNS.get(
            lang_code, patterns.CERTAINTY_PATTERNS.get("en", [])
        )

        compiled = {
            "prescriptive": [
                re.compile(pattern, re.IGNORECASE | re.UNICODE) for pattern in prescriptive
            ],
            "advice": [
                (re.compile(pattern, re.IGNORECASE | re.UNICODE), replacement)
                for pattern, replacement in advice
            ],
            "opinion": [
                (re.compile(pattern, re.IGNORECASE | re.UNICODE), replacement)
                for pattern, replacement in opinion
            ],
            "certainty": [
                (re.compile(pattern, re.IGNORECASE | re.UNICODE), replacement)
                for pattern, replacement in certainty
            ],
        }

        self._compiled_patterns_cache[lang_code] = compiled
        return compiled

    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text

        Uses simple heuristics based on language-specific indicators.
        Returns 'en' (English) as default for ambiguous cases.

        Args:
            text: Input text to analyze

        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        if not text:
            return "en"

        text_lower = text.lower()
        scores: Dict[str, int] = {}

        # Check for non-Latin scripts first (Japanese, Chinese, Farsi)
        # Japanese: Hiragana, Katakana, and some Kanji
        if any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text):
            return "ja"

        # Chinese: CJK unified ideographs (excluding Japanese-specific)
        if any("\u4e00" <= c <= "\u9fff" for c in text) and not any(
            "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text
        ):
            return "zh"

        # Farsi/Persian: Arabic script with Persian-specific characters
        if any("\u0600" <= c <= "\u06ff" for c in text):
            return "fa"

        # For Latin-script languages, use word indicators
        for lang_code, indicators in MultilingualPatterns.LANGUAGE_INDICATORS.items():
            # Skip non-Latin script languages (already handled above)
            if lang_code in ("ja", "zh", "fa"):
                continue

            # Use word boundary matching to avoid false positives
            score = 0
            for indicator in indicators:
                # Count occurrences as whole words
                pattern = rf"\b{re.escape(indicator)}\b"
                matches = re.findall(pattern, text_lower)
                score += len(matches)

            if score > 0:
                scores[lang_code] = score

        # If no strong signal, default to English
        if not scores:
            return "en"

        # Get the highest scoring language
        max_score = max(scores.values())
        # scores.get returns Optional[int] but we know all values exist since we just populated the dict
        detected = max(scores, key=scores.get)  # type: ignore[arg-type]

        # Require a minimum threshold to override English default
        # This prevents false detection from common words
        if max_score < self.language_detection_threshold:
            return "en"

        logger.debug(
            "Language detected",
            detected_language=detected,
            scores=scores,
        )

        return detected

    def process(
        self,
        text: str,
        asset_class: AssetClass = AssetClass.EQUITY,
        region: Region = Region.US,
        language: SupportedLanguage = SupportedLanguage.AUTO,
    ) -> GuardrailResult:
        """
        Process text through the compliance guardrail

        Args:
            text: Input text to process
            asset_class: Type of asset for disclaimer customization
            region: User's region for compliance requirements
            language: Language of the text (AUTO for auto-detection)

        Returns:
            GuardrailResult with processed text and modification details
        """
        if not text or not text.strip():
            return GuardrailResult(
                action=GuardrailAction.PASSED,
                original_text=text,
                processed_text=text,
            )

        # Determine language
        if language == SupportedLanguage.AUTO:
            lang_code = self.detect_language(text)
        else:
            lang_code = language.value

        violations: List[str] = []
        modifications: List[str] = []
        processed_text = text

        # Get compiled patterns for the detected/specified language
        patterns = self._get_compiled_patterns(lang_code)

        # Also get English patterns for mixed-language content
        english_patterns = self._get_compiled_patterns("en") if lang_code != "en" else None

        # Step 1: Scan for violations in primary language
        violations.extend(self._scan_for_prescriptive_verbs(text, patterns["prescriptive"]))
        violations.extend(self._scan_for_patterns(text, patterns["advice"], "Advice"))
        violations.extend(self._scan_for_patterns(text, patterns["opinion"], "Opinion"))
        violations.extend(self._scan_for_patterns(text, patterns["certainty"], "Certainty"))

        # Also scan for English patterns in non-English text (mixed content)
        if english_patterns:
            violations.extend(
                self._scan_for_prescriptive_verbs(text, english_patterns["prescriptive"])
            )
            violations.extend(self._scan_for_patterns(text, english_patterns["advice"], "Advice"))

        # Step 2: If violations found in strict mode, block the content
        if self.strict_mode and len(violations) > self.strict_mode_violation_limit:
            logger.warning(
                "Content blocked due to excessive violations",
                violation_count=len(violations),
                language=lang_code,
            )
            return GuardrailResult(
                action=GuardrailAction.BLOCKED,
                original_text=text,
                processed_text="",
                violations_found=violations,
                confidence=0.0,
                detected_language=lang_code,
            )

        # Step 3: Remove/replace advice-like language
        processed_text, advice_mods = self._remove_patterns(processed_text, patterns["advice"])
        modifications.extend(advice_mods)

        # Also process English patterns for mixed content
        if english_patterns:
            processed_text, en_mods = self._remove_patterns(
                processed_text, english_patterns["advice"]
            )
            modifications.extend(en_mods)

        # Step 4: Remove/replace opinion as fact patterns
        processed_text, opinion_mods = self._remove_patterns(processed_text, patterns["opinion"])
        modifications.extend(opinion_mods)

        # Step 5: Convert certainty language to descriptive
        processed_text, certainty_mods = self._remove_patterns(
            processed_text, patterns["certainty"]
        )
        modifications.extend(certainty_mods)

        # Step 6: Ensure descriptive tone (English-specific)
        if lang_code == "en":
            processed_text, tone_mods = self._ensure_descriptive_tone(processed_text)
            modifications.extend(tone_mods)

        # Step 7: Clean up any grammar issues from replacements
        if modifications:
            processed_text = self._cleanup_grammar(processed_text)

        # Step 8: Check and add disclaimer if needed
        disclaimer_added = False
        if self.auto_add_disclaimer and not self._has_disclaimer(processed_text, lang_code):
            disclaimer = self.disclaimer_generator.generate(
                asset_class=asset_class,
                region=region,
                include_general=True,
            )
            processed_text = self._add_disclaimer(processed_text, disclaimer)
            disclaimer_added = True
            modifications.append("Added compliance disclaimer")

        # Determine action
        if not modifications and not violations:
            action = GuardrailAction.PASSED
        else:
            action = GuardrailAction.MODIFIED

        # Calculate confidence based on modifications
        confidence = self._calculate_confidence(len(violations), len(modifications))

        logger.info(
            "Guardrail processing complete",
            action=action.value,
            violations=len(violations),
            modifications=len(modifications),
            disclaimer_added=disclaimer_added,
            language=lang_code,
        )

        return GuardrailResult(
            action=action,
            original_text=text,
            processed_text=processed_text,
            modifications=modifications,
            violations_found=violations,
            disclaimer_added=disclaimer_added,
            confidence=confidence,
            detected_language=lang_code,
        )

    def scan_only(
        self,
        text: str,
        language: SupportedLanguage = SupportedLanguage.AUTO,
    ) -> List[str]:
        """
        Scan text for violations without modifying it

        Args:
            text: Input text to scan
            language: Language of the text (AUTO for auto-detection)

        Returns:
            List of violations found
        """
        if language == SupportedLanguage.AUTO:
            lang_code = self.detect_language(text)
        else:
            lang_code = language.value

        patterns = self._get_compiled_patterns(lang_code)

        violations = []
        violations.extend(self._scan_for_prescriptive_verbs(text, patterns["prescriptive"]))
        violations.extend(self._scan_for_patterns(text, patterns["advice"], "Advice"))
        violations.extend(self._scan_for_patterns(text, patterns["opinion"], "Opinion"))
        violations.extend(self._scan_for_patterns(text, patterns["certainty"], "Certainty"))

        # Also check English patterns for mixed content
        if lang_code != "en":
            english_patterns = self._get_compiled_patterns("en")
            violations.extend(
                self._scan_for_prescriptive_verbs(text, english_patterns["prescriptive"])
            )
            violations.extend(self._scan_for_patterns(text, english_patterns["advice"], "Advice"))

        return violations

    def is_compliant(
        self,
        text: str,
        language: SupportedLanguage = SupportedLanguage.AUTO,
    ) -> bool:
        """
        Check if text is already compliant

        Args:
            text: Input text to check
            language: Language of the text (AUTO for auto-detection)

        Returns:
            True if text is compliant, False otherwise
        """
        if language == SupportedLanguage.AUTO:
            lang_code = self.detect_language(text)
        else:
            lang_code = language.value

        violations = self.scan_only(text, language)
        has_disclaimer = self._has_disclaimer(text, lang_code)
        return len(violations) == 0 and (has_disclaimer or not self.auto_add_disclaimer)

    def add_disclaimer(
        self,
        text: str,
        asset_class: AssetClass = AssetClass.EQUITY,
        region: Region = Region.US,
        language: SupportedLanguage = SupportedLanguage.AUTO,
    ) -> str:
        """
        Add a disclaimer to text if not already present

        Args:
            text: Input text
            asset_class: Type of asset for disclaimer customization
            region: User's region for compliance requirements
            language: Language of the text (AUTO for auto-detection)

        Returns:
            Text with disclaimer added
        """
        if language == SupportedLanguage.AUTO:
            lang_code = self.detect_language(text)
        else:
            lang_code = language.value

        if self._has_disclaimer(text, lang_code):
            return text

        disclaimer = self.disclaimer_generator.generate(
            asset_class=asset_class,
            region=region,
            include_general=True,
        )
        return self._add_disclaimer(text, disclaimer)

    def _scan_for_prescriptive_verbs(
        self,
        text: str,
        compiled_patterns: List,
    ) -> List[str]:
        """Scan for prescriptive verbs in text"""
        violations = []
        for pattern in compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                violations.append(f"Prescriptive verb found: {pattern.pattern}")
        return violations

    def _scan_for_patterns(
        self,
        text: str,
        compiled_patterns: List[Tuple],
        pattern_type: str,
    ) -> List[str]:
        """Scan for specific patterns in text"""
        violations = []
        for pattern, _ in compiled_patterns:
            if pattern.search(text):
                violations.append(f"{pattern_type} pattern found: {pattern.pattern}")
        return violations

    def _remove_patterns(
        self,
        text: str,
        compiled_patterns: List[Tuple],
    ) -> Tuple[str, List[str]]:
        """Remove or replace patterns in text"""
        modifications = []
        result = text

        for pattern, replacement in compiled_patterns:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                modifications.append(f"Replaced pattern: {pattern.pattern}")

        return result, modifications

    def _ensure_descriptive_tone(self, text: str) -> Tuple[str, List[str]]:
        """
        Ensure text has descriptive-only tone

        Converts remaining prescriptive verbs to descriptive alternatives
        """
        modifications = []
        result = text

        # Generic prescriptive to descriptive conversions - improved for sentence context
        # These patterns are designed to work with common sentence structures
        prescriptive_replacements: Dict[str, str] = {
            # "You should/must" patterns - preserve sentence flow
            r"\b(you |one )?should buy\b": "purchasing options are available for",
            r"\b(you |one )?should sell\b": "selling options are available for",
            r"\b(you |one )?should invest( in)?\b": "investment options exist for",
            r"\b(you |one )?should hold\b": "holding remains an option for",
            r"\b(you |one )?should consider\b": "one may analyze",
            r"\b(you |one )?must buy\b": "purchasing is possible for",
            r"\b(you |one )?must sell\b": "selling is possible for",
            r"\b(you |one )?need to buy\b": "buying is an available option for",
            r"\b(you |one )?need to sell\b": "selling is an available option for",
            r"\b(it'?s |it is )?better to buy\b": "buying may be considered for",
            r"\b(it'?s |it is )?better to sell\b": "selling may be considered for",
            # Recommendation patterns
            r"\b(i |we )?(strongly )?recommend buying\b": "buying is one available option",
            r"\b(i |we )?(strongly )?recommend selling\b": "selling is one available option",
            r"\b(i |we )?(strongly )?recommend investing( in)?\b": "investing is one available option",
            r"\b(i |we )?advise buying\b": "buying is one available option",
            r"\b(i |we )?advise selling\b": "selling is one available option",
            r"\b(i |we )?suggest buying\b": "buying is one available option",
            r"\b(i |we )?suggest selling\b": "selling is one available option",
            # Additional prescriptive patterns
            r"\b(you |one )?ought to (buy|sell|invest)\b": "\\2ing is an available option",
            r"\b(you |one )?have to (buy|sell)\b": "\\2ing is an available option",
        }

        for pattern, replacement in prescriptive_replacements.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            if compiled_pattern.search(result):
                result = compiled_pattern.sub(replacement, result)
                modifications.append(f"Converted prescriptive phrase: {pattern}")

        return result, modifications

    def _cleanup_grammar(self, text: str) -> str:
        """
        Clean up common grammar issues after pattern replacement

        Args:
            text: Text to clean up

        Returns:
            Text with grammar issues fixed
        """
        result = text

        # Fix common grammar issues from pattern replacement
        grammar_fixes = [
            # Fix double articles
            (r"\ba an\b", "an"),
            (r"\ban a\b", "a"),
            (r"\bthe the\b", "the"),
            # Fix double "is"
            (r"\bis is\b", "is"),
            (r"\bare are\b", "are"),
            (r"\bhas has\b", "has"),
            (r"\bhave have\b", "have"),
            # Fix "is has" type issues
            (r"\bis has\b", "has"),
            (r"\bare have\b", "have"),
            # Fix spacing issues
            (r"\s{2,}", " "),
            # Fix sentence-initial lowercase after replacement
            # Captures optional whitespace + first lowercase letter, uppercases just the letter
            (r"^(\s*)([a-z])", lambda m: m.group(1) + m.group(2).upper()),
        ]

        for pattern, replacement in grammar_fixes:
            if callable(replacement):
                result = re.sub(pattern, replacement, result)
            else:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result.strip()

    def _has_disclaimer(self, text: str, lang_code: str = "en") -> bool:
        """
        Check if text contains a required disclaimer

        Args:
            text: Text to check
            lang_code: Language code to check disclaimers for

        Returns:
            True if disclaimer is present
        """
        text_lower = text.lower()

        # Always check ALL language disclaimer phrases to handle mixed content
        # and cases where language detection may not be accurate
        all_phrases: List[str] = []
        for phrases in MultilingualPatterns.DISCLAIMER_PHRASES.values():
            all_phrases.extend(phrases)

        return any(phrase in text_lower for phrase in all_phrases)

    def _add_disclaimer(self, text: str, disclaimer: str) -> str:
        """Add disclaimer to text"""
        # Ensure proper spacing
        if text.endswith("\n\n"):
            return f"{text}{disclaimer}"
        elif text.endswith("\n"):
            return f"{text}\n{disclaimer}"
        else:
            return f"{text}\n\n{disclaimer}"

    def _calculate_confidence(self, violation_count: int, modification_count: int) -> float:
        """
        Calculate confidence score based on modifications

        Higher confidence = fewer modifications needed
        """
        if violation_count == 0 and modification_count == 0:
            return 1.0

        # Base confidence
        base_confidence = 0.95

        # Reduce for each violation/modification
        reduction_per_item = 0.05
        total_reduction = (violation_count + modification_count) * reduction_per_item

        return max(0.5, base_confidence - total_reduction)

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes

        Returns:
            List of supported language codes
        """
        return list(MultilingualPatterns.PRESCRIPTIVE_VERBS.keys())


# Global guardrail instance for convenience
compliance_guardrail = ComplianceGuardrail()
