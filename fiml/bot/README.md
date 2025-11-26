# FIML Educational Bot

Multi-platform educational trading bot with BYOK (Bring Your Own Key) architecture.

## Phase 1 Implementation Status

### ✅ Completed (Sprint 1.1 - BYOK Foundation)

**Component 1: UserProviderKeyManager**
- ✅ Encrypted API key storage with Fernet
- ✅ Key format validation (regex patterns)
- ✅ Live API key testing for major providers
- ✅ Quota tracking and warnings
- ✅ Audit logging
- ✅ Multi-provider support (Alpha Vantage, Polygon, Finnhub, FMP)

**Component 2: FIMLProviderConfigurator**
- ✅ Per-user FIML configuration
- ✅ Provider priority system (user keys > platform keys)
- ✅ Automatic fallback to free providers
- ✅ Usage tracking and quota management
- ✅ Provider status monitoring

**Component 4: TelegramBotAdapter**
- ✅ Bot command handlers (/start, /help, /addkey, /listkeys, etc.)
- ✅ Multi-step conversation flow for key onboarding
- ✅ Inline keyboards for interactive UI
- ✅ Telegram markdown formatting
- ✅ Key management (/addkey, /removekey, /testkey, /status)
- ✅ Dynamic lesson loading from YAML files
- ✅ Key removal callback handler

### ✅ Completed (Sprint 2.1 - Educational Features)

**Component 6: LessonContentEngine**
- ✅ YAML lesson loading
- ✅ Dynamic lesson rendering
- ✅ Progress tracking
- ✅ Prerequisite checking
- ✅ 20 lesson files available

**Component 7: QuizSystem**
- ✅ Quiz session management
- ✅ Multiple question types (multiple choice, true/false, numeric)
- ✅ Score calculation
- ✅ XP rewards

**Component 8: AIMentorService**
- ✅ 3 mentor personas (Maya, Theo, Zara)
- ✅ Context-aware responses
- ✅ Educational tone enforcement
- ✅ Lesson suggestions

**Component 9: GamificationEngine**
- ✅ XP and leveling system
- ✅ Daily streaks
- ✅ Badge awards
- ✅ Progress tracking

**Component 11: EducationalComplianceFilter**
- ✅ Detects financial advice language
- ✅ Blocks investment recommendations
- ✅ Regional compliance checks
- ✅ Automatic disclaimers

## Quick Start

### 1. Get a Telegram Bot Token

Talk to [@BotFather](https://t.me/BotFather) on Telegram:
1. Send `/newbot`
2. Follow instructions to create your bot
3. Copy the bot token

### 2. Configure Environment

Create a `.env` file:

```bash
# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Encryption key for API keys (optional - auto-generated if not set)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-encryption-key-here

# Storage path for encrypted keys (optional)
KEY_STORAGE_PATH=./data/keys
```

### 3. Install Dependencies

```bash
# Install FIML with bot dependencies
pip install -e .

# Or just the new dependencies
pip install python-telegram-bot>=20.7 cryptography>=41.0.0
```

### 4. Run the Bot

```bash
# From repository root
python -m fiml.bot.run_bot

# Or directly
cd fiml/bot
python run_bot.py
```

### 5. Test the Bot

Open Telegram and find your bot. Try these commands:

- `/start` - Welcome message
- `/help` - List all commands
- `/addkey` - Add an API key (interactive flow)
- `/listkeys` - View your connected providers
- `/status` - Check usage and limits
- `/testkey` - Test if your keys work
- `/removekey` - Remove a provider

## Architecture

```
┌────────────────────────────────┐
│  TelegramBotAdapter            │  ← User Interface (Commands & Conversations)
└────────────────────────────────┘
              ↓
┌────────────────────────────────┐
│  FIMLProviderConfigurator      │  ← Provider Selection & Configuration
└────────────────────────────────┘
              ↓
┌────────────────────────────────┐
│  UserProviderKeyManager        │  ← Encrypted Key Storage & Validation
└────────────────────────────────┘
              ↓
┌────────────────────────────────┐
│  User's API Keys → FIML        │  ← Data Access
└────────────────────────────────┘
```

## Supported Providers

### Free Tier Available

1. **Alpha Vantage** (stocks, forex, crypto)
   - Free: 5 requests/minute, 500/day
   - Get key: https://www.alphavantage.co/support/#api-key

2. **Finnhub** (stocks, forex, crypto)
   - Free: 60 requests/minute
   - Get key: https://finnhub.io/pricing

3. **Financial Modeling Prep** (stocks, crypto, forex)
   - Free: 250 requests/day
   - Get key: https://site.financialmodelingprep.com/developer/docs

### Paid Only

4. **Polygon.io** (stocks, options, forex, crypto)
   - Starter: $199/mo
   - Get key: https://polygon.io/pricing

### Always Free (No Key)

5. **Yahoo Finance** (stocks, ETFs, indices)
   - No API key needed
   - Used as fallback

## User Flow Example

```
User: /addkey
Bot: Choose which data provider:
     1️⃣ Alpha Vantage (✓ Free tier)
     2️⃣ Polygon.io (Paid only)
     ...

User: [Selects Alpha Vantage]
Bot: Get your free key: https://...
     Once you have it, paste it here.

User: ABC123XYZ456789
Bot: 🔄 Testing your key...
     ✅ Key validated! (Free tier: 5 req/min)
     
     Save this key? [Yes] [Cancel]

User: [Yes]
Bot: 🎉 API Key Saved!
     
     What's next:
     • /listkeys - View all your keys
     • /status - Check usage
     • /lesson - Start learning
```

## Security

- **Encryption**: All API keys encrypted with Fernet (AES 128)
- **Validation**: Keys tested before storage
- **Audit**: All key operations logged
- **Isolation**: Each user's keys stored separately
- **No Logging**: Keys never appear in plaintext logs

## Development

### Project Structure

```
fiml/bot/
├── __init__.py
├── run_bot.py              # Entry point
├── core/
│   ├── __init__.py
│   ├── gateway.py          # Component 3: Bot gateway
│   ├── key_manager.py      # Component 1: Key management
│   └── provider_configurator.py  # Component 2: FIML config
├── adapters/
│   ├── __init__.py
│   └── telegram_adapter.py # Component 4: Telegram bot
├── education/
│   ├── ai_mentor.py        # Component 8: AI mentors
│   ├── compliance_filter.py # Component 11: Compliance
│   ├── fiml_adapter.py     # Component 10: FIML integration
│   ├── gamification.py     # Component 9: XP & badges
│   ├── lesson_engine.py    # Component 6: Lessons
│   └── quiz_system.py      # Component 7: Quizzes
└── content/
    └── lessons/            # 20 YAML lesson files
```

### Adding New Providers

1. Add pattern to `UserProviderKeyManager.KEY_PATTERNS`
2. Add info to `UserProviderKeyManager.PROVIDER_INFO`
3. Implement test method `_test_<provider_name>`
4. Add provider initialization in `FIMLProviderConfigurator`

### Adding New Lessons

1. Create a YAML file in `content/lessons/`
2. Include required fields: `id`, `title`, `difficulty`, `sections`
3. Add quiz questions (optional)
4. The lesson will be auto-discovered on bot startup

### Testing

```bash
# Run all bot tests (168 tests)
pytest tests/bot/ -v

# Run bot in development mode
python -m fiml.bot.run_bot

# Test key validation
python -c "
from fiml.bot.core.key_manager import UserProviderKeyManager
km = UserProviderKeyManager()
print(km.validate_key_format('alpha_vantage', 'ABC123XYZ456789X'))
"
```

## Launch Checklist

- [x] All bot commands working (/start, /help, /addkey, /listkeys, /removekey, /testkey, /status)
- [x] Educational commands working (/lesson, /quiz, /mentor, /progress)
- [x] 20 lessons available
- [x] Key management with encryption
- [x] 168 tests passing
- [x] Linter checks passing
- [x] No security vulnerabilities

## Contributing

See main [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](../../LICENSE)
