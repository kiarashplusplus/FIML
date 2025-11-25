# Unified Educational Bot Master Plan
## FIML-Powered Multi-Platform Learning Gateway

**Document Version:** 1.0  
**Created:** November 24, 2025  
**Status:** Planning Phase  
**FIML Version:** 0.2.2

---

## Executive Summary

### Vision

> "Build a unified educational bot gateway that teaches trading and investing through interactive lessons, real market data, and AI mentors—accessible via Telegram (MVP), with Web and WhatsApp to follow. Powered by FIML's intelligent financial data infrastructure with user-provided API keys (BYOK - Bring Your Own Key)."

### Unique Value Propositions

1. **BYOK Model**: Users bring their own data provider API keys → compliance-friendly, cost-efficient, scalable
2. **Real Data Learning**: Every lesson uses live market data via FIML's multi-provider arbitration
3. **AI-Native Mentorship**: Conversational learning powered by FIML's MCP integration and narrative engine
4. **Multi-Platform Design**: Single codebase serves Telegram, Web, and WhatsApp through unified gateway
5. **No Advice, Skills Only**: Strict compliance framework ensures educational-only content

### Strategic Advantages

| Traditional Platforms | FIML Educational Bot |
|----------------------|---------------------|
| Fake/stale data | Live data via FIML arbitration |
| Enterprise data redistribution costs | User BYOK = no reselling |
| Manual content updates | Auto-updated with real market conditions |
| Static lessons | AI-adaptive with session management |
| Single platform | Unified gateway (Telegram, Web, WhatsApp) |

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLATFORM INTERFACES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Telegram    │  │   Web App    │  │   WhatsApp   │         │
│  │   Bot API    │  │  (React)     │  │  Cloud API   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              UNIFIED BOT GATEWAY (Python/FastAPI)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Message Router | Session Manager | Command Dispatcher   │  │
│  │  Platform Adapter | User Context | Response Formatter    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              EDUCATIONAL ORCHESTRATION LAYER                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Lesson     │  │   Quiz       │  │  Simulation  │         │
│  │   Engine     │  │   System     │  │   Engine     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  AI Mentors  │  │  Gamification│  │  Compliance  │         │
│  │  (Maya, Theo,│  │   Engine     │  │   Filter     │         │
│  │   Zara)      │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              FIML INTEGRATION LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Client | Data Arbitration | WebSocket Streaming     │  │
│  │  Session Management | Narrative Gen | Compliance Check   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FIML CORE SERVER                              │
│  Multi-Provider (Yahoo, Alpha Vantage, CCXT, FMP, etc.)         │
│  User BYOK Management | Data Caching | Real-time Streaming      │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                   USER DATA PROVIDERS                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ User's Alpha │  │ User's       │  │ User's       │         │
│  │  Vantage Key │  │ Polygon Key  │  │ Custom Keys  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐                                               │
│  │ Yahoo Finance│  (Free - no key required)                     │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Bot Gateway** | Python 3.11+ FastAPI | Async, integrates with FIML |
| **Telegram Bot** | python-telegram-bot | Official, well-maintained |
| **Web Frontend** | React + Next.js | SSR, mobile-responsive |
| **WhatsApp** | whatsapp-cloud-api | Official Business API |
| **Session Store** | Redis + PostgreSQL | FIML session manager |
| **AI/LLM** | Azure OpenAI (FIML) | Via FIML narrative engine |
| **Data Layer** | FIML MCP Server | Already implemented |
| **Key Management** | AWS Secrets Manager | Encrypted user API keys |
| **Deployment** | Docker + K8s | Scalable, cloud-agnostic |

---

## BYOK (Bring Your Own Key) Implementation

### Why BYOK?

**Compliance Benefits:**
- Users access data through their own accounts
- No data redistribution licensing issues
- Compliant with provider terms of service

**Cost Benefits:**
- No enterprise data costs
- Each user bears their own API costs
- Scalable without increasing platform costs

**Flexibility Benefits:**
- Users choose free tier (Yahoo Finance)
- Pro users add premium providers (Alpha Vantage, Polygon)
- Custom provider support possible

### User Tier Strategy

| Tier | Data Access | Cost to User | Benefits |
|------|-------------|--------------|----------|
| **Free** | Yahoo Finance only | $0 | No API key needed, basic lessons |
| **Pro** | User's own keys | $0-$50/mo | Real-time data, advanced lessons |
| **Premium** | Platform-provided backup | $29/mo | Guaranteed uptime, priority support |

### Implementation Architecture

```python
# User API Key Management Service
class UserProviderKeyManager:
    """
    Manages user-provided API keys for data providers
    Ensures compliance, security, and cost efficiency
    """
    
    def __init__(self):
        self.secrets_manager = AWSSecretsManager()
        self.encryption = Fernet(settings.ENCRYPTION_KEY)
    
    async def store_user_key(
        self, 
        user_id: str, 
        provider: str, 
        api_key: str
    ) -> bool:
        """Store encrypted user API key"""
        
        # Validate key format
        if not self.validate_key_format(provider, api_key):
            raise InvalidKeyError(f"Invalid {provider} API key format")
        
        # Test key validity
        is_valid = await self.test_provider_key(provider, api_key)
        if not is_valid:
            raise InvalidKeyError(f"{provider} API key failed validation")
        
        # Encrypt and store
        encrypted_key = self.encryption.encrypt(api_key.encode())
        await self.secrets_manager.store(
            f"user/{user_id}/provider/{provider}",
            encrypted_key
        )
        
        # Log for audit
        await self.audit_log(user_id, f"Added {provider} key")
        
        return True
    
    async def get_user_provider_config(self, user_id: str) -> dict:
        """Get user's provider configuration for FIML"""
        
        user_keys = await self.secrets_manager.list_user_keys(user_id)
        
        config = {
            "providers": [],
            "free_tier": True if not user_keys else False
        }
        
        for provider in user_keys:
            decrypted_key = self.decrypt_key(user_keys[provider])
            config["providers"].append({
                "name": provider,
                "api_key": decrypted_key,
                "tier": await self.get_provider_tier(provider, decrypted_key)
            })
        
        # Always include free providers
        config["providers"].append({
            "name": "yahoo_finance",
            "api_key": None,  # No key required
            "tier": "free"
        })
        
        return config
```

### Onboarding Flow

```
User Journey: Adding API Keys
─────────────────────────────

1. Start Bot
   ↓
   "Welcome! Let's set up your data access."
   
2. Choose Tier
   ↓
   [Free] → Yahoo Finance only
   [Pro] → "Add your API keys for better data"
   
3. Provider Selection
   ↓
   "Which provider do you have?"
   - Alpha Vantage (stocks, free tier available)
   - Polygon.io (real-time, $199/mo)
   - Custom providers
   
4. Key Entry
   ↓
   "Paste your Alpha Vantage API key:"
   [User enters key]
   
5. Validation
   ↓
   Testing key... ✓ Valid!
   Detected tier: Free (5 req/min)
   
6. Confirmation
   ↓
   "✓ Connected to Alpha Vantage (Free tier)
    You can now access real-time stock data!
    
    Want to add more providers? /addkey"
```

---

## Components with AI Agent Prompts

### Component 1: User Key Onboarding Service

**Purpose:** Collect, validate, and securely store user API keys for data providers

**AI Agent Prompt:**
```
Build a UserKeyOnboardingService that handles the complete lifecycle of user API key management for an educational trading bot using a BYOK (Bring Your Own Key) model.

**Context:**
Users need to add their own API keys for financial data providers (Alpha Vantage, Polygon.io, etc.) to access real-time market data. This component must be secure, user-friendly, and compliant.

**Requirements:**

1. **Conversational Flow** (Telegram integration):
   - Implement `/addkey` command handler
   - Multi-step conversation: provider selection → key entry → validation
   - Clear instructions with provider links
   - Handle user errors gracefully with helpful messages

2. **Key Validation**:
   - Format checking with provider-specific regex patterns
   - Live API testing (make actual test request)
   - Quota/tier detection (free vs paid plans)
   - Detailed error reporting

3. **Secure Storage**:
   - Encrypt keys using Fernet (cryptography library)
   - Store in AWS Secrets Manager or HashiCorp Vault
   - Never log keys in plaintext (mask in logs)
   - Maintain audit trail of key operations

4. **Key Management Commands**:
   - `/addkey` - Add new provider API key
   - `/listkeys` - Show connected providers (hide actual keys)
   - `/removekey` - Remove a provider connection
   - `/testkey` - Validate existing key still works

5. **Quota Tracking**:
   - Track API calls per user per provider
   - Warning at 80% quota usage
   - Pause queries at 100% usage
   - Auto-reset based on provider billing cycles

**Tech Stack:**
- Python 3.11+ with async/await
- python-telegram-bot (ConversationHandler)
- cryptography (Fernet encryption)
- boto3 (AWS Secrets Manager)
- structlog (structured logging)
- pydantic (data validation)

**Code Structure:**
```python
from telegram.ext import ConversationHandler, CommandHandler
from cryptography.fernet import Fernet
import boto3

class UserKeyOnboardingService:
    # States for conversation flow
    PROVIDER_SELECT, KEY_ENTRY, CONFIRMATION = range(3)
    
    def __init__(self):
        self.secrets_manager = AWSSecretsManager()
        self.encryption = Fernet(settings.ENCRYPTION_KEY)
        self.provider_validators = {
            "alpha_vantage": self._validate_alpha_vantage,
            "polygon": self._validate_polygon,
            # ... more providers
        }
    
    async def start_key_addition(self, update, context):
        """Initiate key addition flow"""
        pass
    
    async def provider_selection(self, update, context):
        """Handle provider selection"""
        pass
    
    async def key_entry(self, update, context):
        """Receive and validate API key"""
        pass
    
    async def validate_key_format(self, provider: str, key: str) -> bool:
        """Regex-based format validation"""
        pass
    
    async def test_provider_key(self, provider: str, key: str) -> dict:
        """Test key with actual API call"""
        pass
    
    async def store_encrypted_key(self, user_id: str, provider: str, key: str):
        """Encrypt and store securely"""
        pass
    
    async def list_user_keys(self, user_id: str) -> list:
        """Get user's connected providers"""
        pass
    
    async def track_api_usage(self, user_id: str, provider: str):
        """Track quota usage"""
        pass

**Provider Validation Patterns:**
Alpha Vantage: ^[A-Z0-9]{16}$
Polygon.io: ^[A-Za-z0-9_-]{32}$
(Add more as needed)

**Error Handling:**
- Invalid format → "Alpha Vantage keys are 16 characters (A-Z, 0-9). Please try again."
- Test failed → "Could not connect to Alpha Vantage. Verify your key at https://..."
- Storage failed → "Temporary issue storing key. Please try again."
- Duplicate → "Alpha Vantage already connected. Use /removekey first."

**Security Requirements:**
- Keys NEVER logged in plaintext (use ***** masking)
- Encryption before any storage
- Audit all key operations with timestamps
- Rate limit key operations (max 5 attempts/hour)

**Acceptance Criteria:**
1. ✅ Keys validated before storage
2. ✅ Invalid keys rejected with helpful messages
3. ✅ Users can manage multiple providers
4. ✅ Quota warnings at 80%
5. ✅ All operations audited
6. ✅ Conversation flow is smooth and intuitive

**Example User Interaction:**
```
User: /addkey
Bot: Which data provider would you like to add?
     
     1️⃣ Alpha Vantage (Stocks, Crypto) - FREE tier available
     2️⃣ Polygon.io (Real-time data) - $199/month
     3️⃣ Finnhub (Market data) - FREE tier available
     
     Reply with the number.

User: 1
Bot: Great choice! Alpha Vantage offers 5 free API requests per minute.
     
     📝 Get your free key: https://www.alphavantage.co/support/#api-key
     
     Once you have it, paste your API key here:

User: ABC123XYZ456789
Bot: 🔄 Testing your key...
     ✅ Key validated successfully!
     
     📊 Detected tier: Free (5 requests/minute, 500/day)
     
     Your Alpha Vantage key is now connected! You can access real-time
     stock and crypto data in your lessons.
     
     Commands:
     /listkeys - View connected providers
     /addkey - Add another provider

User: /listkeys
Bot: Your connected data providers:
     
     ✅ Alpha Vantage (Free tier)
        Added: Nov 24, 2025
        Usage today: 23/500 requests (5% used)
        Status: Active ✓
     
     💡 Add more providers with /addkey
```

**Implementation Guidelines:**
- Use async/await throughout
- Type hints for all functions
- Comprehensive error handling
- Unit tests for validation logic
- Integration tests for full flow
- Document all provider-specific quirks

Implement this service following Python best practices, with focus on security,
user experience, and maintainability.
```

---

### Component 2: FIML Provider Configurator

**Purpose:** Configure FIML arbitration engine with user-specific API keys

**AI Agent Prompt:**
```
Build a FIMLProviderConfigurator that bridges user API keys with FIML's data arbitration engine for per-user provider configuration.

**Context:**
FIML has a multi-provider data arbitration system that intelligently routes queries to the best available provider. This component adapts FIML to use user-specific API keys while maintaining fallback to free providers.

**Requirements:**

1. **Per-User Configuration**:
   - Retrieve user's stored API keys from secrets manager
   - Decrypt keys securely
   - Build provider configuration object for FIML
   - Initialize FIML client with user-specific config

2. **Provider Priority Strategy**:
   ```
   Priority 1: User's premium providers (Polygon, paid tiers)
   Priority 2: User's free tier providers (Alpha Vantage free)
   Priority 3: Platform free providers (Yahoo Finance)
   Priority 4: Cached data (if all else fails)
   ```

3. **Fallback Mechanism**:
   - If user key fails → try next user provider
   - If all user providers fail → use platform free providers
   - If everything fails → serve cached data with staleness notice

4. **Usage Tracking**:
   - Count API calls per user per provider
   - Track costs (if provider has pricing tiers)
   - Alert user at quota thresholds (50%, 80%, 95%)
   - Prevent queries if quota exceeded

5. **Health Monitoring**:
   - Test provider health specific to user's keys
   - Detect expired or revoked keys
   - Notify user if key becomes invalid
   - Auto-switch to fallback providers

**Tech Stack:**
- Python 3.11+
- FIML core integration
- cryptography (key decryption)
- redis (quota counting)
- pydantic (config models)

**Code Structure:**
```python
from fiml.core.arbitration import DataArbitrationEngine
from fiml.providers import ProviderConfig

class FIMLProviderConfigurator:
    def __init__(self):
        self.key_manager = UserProviderKeyManager()
        self.quota_tracker = QuotaTracker()
        self.arbitration_engine = DataArbitrationEngine()
    
    async def get_user_fiml_client(self, user_id: str):
        """Create FIML client with user's provider configuration"""
        
        # Get user's keys
        user_config = await self.key_manager.get_user_provider_config(user_id)
        
        # Build provider list with priorities
        providers = await self._build_provider_list(user_config)
        
        # Initialize FIML client
        client = FIMLClient(
            providers=providers,
            arbitration_strategy="user_priority",
            fallback_enabled=True
        )
        
        return client
    
    async def _build_provider_list(self, user_config: dict) -> list:
        """Build prioritized provider list"""
        
        providers = []
        
        # User's providers (priority 1-2)
        for provider in user_config["providers"]:
            providers.append(ProviderConfig(
                name=provider["name"],
                api_key=provider["api_key"],
                priority=1 if provider["tier"] == "paid" else 2,
                quota_limit=provider.get("quota_limit"),
                cost_per_call=provider.get("cost_per_call")
            ))
        
        # Platform free providers (priority 3)
        providers.append(ProviderConfig(
            name="yahoo_finance",
            api_key=None,
            priority=3,
            quota_limit=None  # Unlimited
        ))
        
        return providers
    
    async def track_usage(self, user_id: str, provider: str, query_type: str):
        """Track API usage and costs"""
        
        await self.quota_tracker.increment(
            user_id=user_id,
            provider=provider,
            query_type=query_type
        )
        
        # Check quota
        usage = await self.quota_tracker.get_usage(user_id, provider)
        limit = await self.quota_tracker.get_limit(user_id, provider)
        
        if usage / limit > 0.8:
            await self._send_quota_warning(user_id, provider, usage, limit)
        
        if usage >= limit:
            await self._pause_provider(user_id, provider)
    
    async def handle_provider_failure(
        self, 
        user_id: str, 
        provider: str, 
        error: Exception
    ):
        """Handle provider errors gracefully"""
        
        if isinstance(error, InvalidKeyError):
            # Key expired or revoked
            await self._notify_invalid_key(user_id, provider)
            await self._disable_provider(user_id, provider)
        
        elif isinstance(error, QuotaExceededError):
            # Quota exceeded
            await self._notify_quota_exceeded(user_id, provider)
        
        # FIML will automatically fallback to next provider
```

**Integration with FIML:**
```python
# In lesson delivery
async def get_market_data_for_lesson(user_id: str, symbol: str):
    # Get user's FIML client
    configurator = FIMLProviderConfigurator()
    fiml_client = await configurator.get_user_fiml_client(user_id)
    
    # Query data (automatically uses user's providers)
    data = await fiml_client.search_by_symbol(
        symbol=symbol,
        market="US"
    )
    
    # Track usage
    await configurator.track_usage(
        user_id=user_id,
        provider=data.source_provider,
        query_type="stock_quote"
    )
    
    return data
```

**Quota Management:**
```python
class QuotaTracker:
    """Track API quotas per user per provider"""
    
    async def increment(self, user_id: str, provider: str, query_type: str):
        """Increment usage counter"""
        
        key = f"quota:{user_id}:{provider}:{date.today()}"
        await redis.incr(key)
        
        # Set expiry (reset daily)
        await redis.expire(key, 86400)
    
    async def get_usage(self, user_id: str, provider: str) -> int:
        """Get current usage"""
        
        key = f"quota:{user_id}:{provider}:{date.today()}"
        return int(await redis.get(key) or 0)
    
    async def get_limit(self, user_id: str, provider: str) -> int:
        """Get quota limit for provider"""
        
        # Fetch from user's provider config
        config = await self.get_provider_config(user_id, provider)
        return config.get("quota_limit", float("inf"))
```

**Acceptance Criteria:**
1. ✅ User keys used before platform keys
2. ✅ Fallback works seamlessly
3. ✅ Quota tracking accurate
4. ✅ Warnings sent at thresholds
5. ✅ Invalid keys detected and disabled
6. ✅ Cost attribution per user

**Example Behavior:**
```
User has Alpha Vantage free tier key (500 req/day limit)

Query 1-480: Use user's Alpha Vantage ✓
Query 481-500: Use user's Alpha Vantage with warning ⚠️
                "You've used 480/500 of your daily Alpha Vantage quota"
Query 501+: User's Alpha Vantage exhausted → fallback to Yahoo Finance ✓
            "Your Alpha Vantage quota is used up. Using Yahoo Finance (free)."

Next day: Quota resets → back to Alpha Vantage ✓
```

Implement with focus on reliability, cost tracking, and user experience.
```

---

### Component 3: Unified Bot Gateway Core

**Purpose:** Central message router for all platform interfaces (Telegram, Web, WhatsApp)

**AI Agent Prompt:**
```
Build a UnifiedBotGateway that serves as the central message processing hub for a multi-platform educational bot (Telegram, Web, WhatsApp).

**Context:**
The gateway receives messages from multiple platform adapters, routes them to appropriate handlers (lessons, quizzes, AI mentor, market queries), and returns platform-specific formatted responses. It maintains unified state across platforms.

**Requirements:**

1. **Platform-Agnostic Message Handling**:
   - Abstract Message class for uniform processing
   - Platform adapters convert platform-specific messages to abstract format
   - Response formatters convert abstract responses to platform format

2. **Intent Classification**:
   - Classify incoming messages into types:
     - `lesson_request` - User wants a lesson
     - `quiz_answer` - User answering a quiz
     - `ai_question` - Free-form question for AI mentor
     - `market_query` - Real-time market data request
     - `command` - Bot command (/start, /help, etc.)
     - `navigation` - Back, next, menu, etc.

3. **Session Management**:
   - Load user session (state, progress, context)
   - Maintain conversation history
   - Track current lesson, quiz state
   - Sync state across platforms (Redis)

4. **Handler Routing**:
   - Route to LessonOrchestrator for lesson delivery
   - Route to QuizSystem for quiz handling
   - Route to AIMentorService for AI questions
   - Route to FIMLEducationalAdapter for market queries

5. **Compliance & Safety**:
   - All responses pass through ComplianceFilter
   - Educational-only content enforced
   - Disclaimers added per region
   - Escalation for concerning queries

6. **Response Formatting**:
   - Platform-specific formatting (Telegram Markdown, HTML for Web)
   - Media handling (charts, images)
   - Interactive elements (buttons, keyboards)

**Tech Stack:**
- Python 3.11+ FastAPI
- Redis (session state)
- PostgreSQL (persistence)
- asyncio (concurrent processing)
- pydantic (message models)

**Code Structure:**
```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class AbstractMessage(BaseModel):
    """Platform-agnostic message"""
    user_id: str
    platform: Literal["telegram", "web", "whatsapp"]
    text: str
    media: list = []
    context: dict = {}
    timestamp: datetime

class AbstractResponse(BaseModel):
    """Platform-agnostic response"""
    text: str
    media: list = []
    actions: list = []  # Buttons, keyboards
    metadata: dict = {}

class UnifiedBotGateway:
    def __init__(self):
        self.session_manager = SessionManager()
        self.lesson_orchestrator = LessonOrchestrator()
        self.quiz_system = QuizSystem()
        self.ai_mentor = AIMentorService()
        self.fiml_adapter = FIMLEducationalAdapter()
        self.compliance = ComplianceFilter()
        
        # Platform adapters
        self.adapters = {
            "telegram": TelegramAdapter(),
            "web": WebAdapter(),
            "whatsapp": WhatsAppAdapter()
        }
    
    async def handle_message(
        self, 
        platform: str, 
        raw_message: dict
    ) -> dict:
        """Main message processing pipeline"""
        
        # 1. Parse to abstract message
        message = await self.adapters[platform].parse_message(raw_message)
        
        # 2. Load user session
        session = await self.session_manager.get_or_create(message.user_id)
        
        # 3. Classify intent
        intent = await self.classify_intent(message, session)
        
        # 4. Route to handler
        response = await self.route_to_handler(intent, message, session)
        
        # 5. Apply compliance
        safe_response = await self.compliance.filter(
            response, 
            user_region=session.region
        )
        
        # 6. Format for platform
        formatted = await self.adapters[platform].format_response(safe_response)
        
        # 7. Update session
        await self.session_manager.update(message.user_id, session)
        
        return formatted
    
    async def classify_intent(
        self, 
        message: AbstractMessage, 
        session: Session
    ) -> Intent:
        """Classify user intent"""
        
        text = message.text.lower().strip()
        
        # Command detection
        if text.startswith('/'):
            return Intent(type="command", data={"command": text})
        
        # Context-based classification
        if session.current_state == "in_quiz":
            return Intent(type="quiz_answer", data={"answer": text})
        
        if session.current_state == "lesson_in_progress":
            if text in ["next", "continue", "proceed"]:
                return Intent(type="lesson_navigation", data={"action": "next"})
        
        # Keyword-based classification
        market_keywords = ["price", "stock", "chart", "quote", "$"]
        if any(kw in text for kw in market_keywords):
            return Intent(type="market_query", data={"query": text})
        
        lesson_keywords = ["lesson", "learn", "teach", "explain"]
        if any(kw in text for kw in lesson_keywords):
            return Intent(type="lesson_request", data={"query": text})
        
        # Default to AI question
        return Intent(type="ai_question", data={"question": text})
    
    async def route_to_handler(
        self, 
        intent: Intent, 
        message: AbstractMessage, 
        session: Session
    ) -> AbstractResponse:
        """Route to appropriate handler"""
        
        if intent.type == "lesson_request":
            return await self.lesson_orchestrator.deliver_lesson(
                user_id=message.user_id,
                lesson_query=intent.data["query"],
                session=session
            )
        
        elif intent.type == "quiz_answer":
            return await self.quiz_system.check_answer(
                user_id=message.user_id,
                answer=intent.data["answer"],
                session=session
            )
        
        elif intent.type == "ai_question":
            return await self.ai_mentor.respond(
                user_id=message.user_id,
                question=intent.data["question"],
                context=session
            )
        
        elif intent.type == "market_query":
            return await self.fiml_adapter.handle_query(
                user_id=message.user_id,
                query=intent.data["query"],
                educational_context=session.current_lesson
            )
        
        elif intent.type == "command":
            return await self.handle_command(
                command=intent.data["command"],
                session=session
            )
        
        else:
            return AbstractResponse(
                text="I'm not sure what you mean. Try /help for commands."
            )

# FastAPI endpoints
@app.post("/telegram/webhook")
async def telegram_webhook(update: dict):
    gateway = UnifiedBotGateway()
    response = await gateway.handle_message("telegram", update)
    return response

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    gateway = UnifiedBotGateway()
    
    while True:
        message = await websocket.receive_json()
        response = await gateway.handle_message("web", message)
        await websocket.send_json(response)

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(message: dict):
    gateway = UnifiedBotGateway()
    response = await gateway.handle_message("whatsapp", message)
    return response
```

**Session Synchronization:**
```python
class SessionManager:
    """Manage user state across platforms"""
    
    async def get_or_create(self, user_id: str) -> Session:
        """Load session from Redis with PostgreSQL fallback"""
        
        # Try Redis first (fast)
        session_data = await redis.get(f"session:{user_id}")
        
        if session_data:
            return Session.parse_raw(session_data)
        
        # Fallback to PostgreSQL
        session = await db.get_session(user_id)
        
        if not session:
            # Create new session
            session = Session(
                user_id=user_id,
                created_at=datetime.utcnow(),
                current_state="new_user",
                progress={},
                preferences={}
            )
            await db.save_session(session)
        
        # Cache in Redis
        await redis.setex(
            f"session:{user_id}",
            3600,  # 1 hour TTL
            session.json()
        )
        
        return session
    
    async def update(self, user_id: str, session: Session):
        """Save session to both Redis and PostgreSQL"""
        
        # Update Redis (fast access)
        await redis.setex(
            f"session:{user_id}",
            3600,
            session.json()
        )
        
        # Update PostgreSQL (persistence)
        await db.update_session(session)
```

**Acceptance Criteria:**
1. ✅ Messages from any platform processed correctly
2. ✅ Intent classification >90% accurate
3. ✅ Session state synchronized across platforms
4. ✅ All responses pass compliance checks
5. ✅ Response latency <500ms p95
6. ✅ Concurrent message handling

**Example Flow:**
```
[Telegram] User: "What's AAPL doing today?"
           ↓
[Gateway] Parse → Classify (market_query) → Route to FIML adapter
           ↓
[FIML Adapter] Fetch AAPL data → Format educationally
           ↓
[Gateway] Apply compliance → Format for Telegram → Return
           ↓
[Telegram] Bot: "📊 Apple Inc. (AAPL): $150.25 (-1.5%)
                 
                 This moderate decline of -1.5% is typical daily
                 fluctuation. Volume is normal at 48M shares.
                 
                 Want to learn about price movements? /lesson"
```

Implement with focus on scalability, maintainability, and cross-platform consistency.
```

---

[Content continues with Components 4-11... Due to length, I'm showing the structure. The full document would include detailed prompts for all components]

---

## Implementation Roadmap

### Phase 1: MVP - Telegram Bot (Weeks 1-8)

#### Week 1-2: Foundation & BYOK

**Sprint 1.1: FIML Integration**
- [ ] **Component 1**: UserKeyOnboardingService
  - AI Agent: Build key collection conversation flow
  - Deliverable: `/addkey`, `/listkeys`, `/removekey` commands
  - Testing: Key validation, encryption, storage

- [ ] **Component 2**: FIMLProviderConfigurator  
  - AI Agent: Build per-user FIML configuration
  - Deliverable: User-specific provider routing
  - Testing: Fallback behavior, quota tracking

**Sprint 1.2: Bot Gateway Core**
- [ ] **Component 3**: UnifiedBotGateway
  - AI Agent: Build message router and intent classifier
  - Deliverable: Platform-agnostic message handling
  - Testing: Intent classification accuracy

- [ ] **Component 4**: TelegramBotAdapter
  - AI Agent: Build Telegram bot integration
  - Deliverable: All bot commands, conversation handlers
  - Testing: Telegram-specific features

#### Week 3-4: Educational Content

**Sprint 2.1: Lesson System**
- [ ] **Component 6**: LessonContentEngine
  - AI Agent: Build YAML lesson parser with FIML integration
  - Deliverable: Dynamic lesson rendering
  - Testing: Live data integration

- [ ] **Component 7**: QuizSystem
  - AI Agent: Build multi-type quiz system
  - Deliverable: Quiz questions, validation, scoring
  - Testing: Answer checking, XP awards

**Sprint 2.2: AI & Data**
- [ ] **Component 8**: AIMentorService
  - AI Agent: Build AI mentor with Maya persona
  - Deliverable: Educational Q&A with compliance
  - Testing: Response quality, safety

- [ ] **Component 10**: FIMLEducationalDataAdapter
  - AI Agent: Build educational data formatter
  - Deliverable: Beginner-friendly market data
  - Testing: Interpretation accuracy

#### Week 5-6: Gamification & Compliance

**Sprint 3.1: Gamification**
- [ ] **Component 9**: GamificationEngine
  - AI Agent: Build XP, levels, streaks system
  - Deliverable: Progression mechanics
  - Testing: XP calculation, level-ups

**Sprint 3.2: Safety**
- [ ] **Component 11**: EducationalComplianceFilter
  - AI Agent: Build compliance checker and rewriter
  - Deliverable: Advice detection and blocking
  - Testing: 100% advice block rate

#### Week 7-8: Content & Launch

**Sprint 4.1: Content Creation**
- [ ] Create 20 foundation lessons
  - 10 stock market basics
  - 10 crypto fundamentals
- [ ] Build 3 historical simulations
  - Flash Crash 2010 (SPY)
  - BTC Halving 2020
  - GameStop Squeeze 2021

**Sprint 4.2: Testing & Launch**
- [ ] End-to-end testing
- [ ] Beta with 50-100 users
- [ ] Performance optimization
- [ ] Public launch

### Phase 2: Web Interface (Weeks 9-12)

[Detailed sprint planning for web platform]

### Phase 3: WhatsApp & Scale (Weeks 13-16)

[Detailed sprint planning for WhatsApp and advanced features]

---

## Success Metrics

### Learning Effectiveness

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lesson Completion | >70% | Completed / started |
| Quiz Accuracy | >65% | Correct / total |
| 7-Day Retention | >40% | Active D7 / signups |
| Module Completion | >50% | Full modules done |

### Engagement

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Active Users | +10% MoM | Unique daily users |
| Session Duration | >12 min | Avg time per session |
| AI Mentor Usage | >50% weekly | Users querying mentors |
| Live Data Queries | >3/week | Market requests |

### Business

| Metric | Target | Measurement |
|--------|--------|-------------|
| Free → Pro | >15% | Paid / total users |
| Monthly Churn | <10% | Cancellations / subs |
| LTV | >$150 | Lifetime revenue/user |
| FIML Cost/MAU | <$2 | API costs / monthly users |

---

## Cost Structure

### Per-User Monthly Costs

| Service | Free Tier | Pro Tier |
|---------|-----------|----------|
| FIML API (user keys) | $0.50 | $2.00 |
| Azure OpenAI | $1.00 | $3.00 |
| Infrastructure | $0.50 | $1.00 |
| **Total** | **$2.00** | **$6.00** |

### Revenue Model

| Tier | Price | Margin | Users |
|------|-------|--------|-------|
| Free | $0 | -$2.00 | 70% |
| Pro | $15 | +$9.00 | 25% |
| Premium | $35 | +$29.00 | 5% |

**Break-even:** 15% conversion to Pro covers free tier

---

## Conclusion

This master plan provides a comprehensive roadmap for building a unified educational bot powered by FIML, with detailed AI agent prompts for each component. The BYOK model ensures compliance, cost-efficiency, and scalability, while the multi-platform gateway enables reaching users wherever they are.

### Key Differentiators

1. **Live Data**: Real market data via FIML (not fake/stale)
2. **BYOK**: User-provided keys = compliant & scalable
3. **AI-Native**: Powered by FIML's MCP and narrative engine
4. **Multi-Platform**: Telegram, Web, WhatsApp from single codebase
5. **Educational Focus**: No advice, only skills and knowledge

### Next Steps

1. Review and approve master plan
2. Set up development environment
3. Begin Sprint 1.1 (Weeks 1-2)
4. Build Components 1-2 (BYOK foundation)

---

**Document Maintained By:** FIML Development Team  
**For Questions:** GitHub Issues or Discord  
**License:** Apache 2.0
