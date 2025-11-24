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

### 🚧 In Progress

**Component 3: UnifiedBotGateway** - Coming next
**Components 6-11** - Educational content, lessons, quizzes, AI mentors

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
│   ├── key_manager.py      # Component 1: Key management
│   └── provider_configurator.py  # Component 2: FIML config
├── adapters/
│   ├── __init__.py
│   └── telegram_adapter.py # Component 4: Telegram bot
├── education/              # Coming: Lessons, quizzes
└── content/                # Coming: Lesson content
```

### Adding New Providers

1. Add pattern to `UserProviderKeyManager.KEY_PATTERNS`
2. Add info to `UserProviderKeyManager.PROVIDER_INFO`
3. Implement test method `_test_<provider_name>`
4. Add provider initialization in `FIMLProviderConfigurator`

### Testing

```bash
# Run bot in development mode
python -m fiml.bot.run_bot

# Test key validation
python -c "
from fiml.bot.core.key_manager import UserProviderKeyManager
km = UserProviderKeyManager()
print(km.validate_key_format('alpha_vantage', 'ABC123XYZ456789X'))
"
```

## Next Steps (Phase 1 Continuation)

### Sprint 1.2 - Bot Gateway (Week 2)
- [ ] Component 3: UnifiedBotGateway (message router)
- [ ] Intent classification
- [ ] Session management integration

### Sprint 2.1 - Educational Content (Week 3-4)
- [ ] Component 6: LessonContentEngine
- [ ] Component 7: QuizSystem
- [ ] 20 foundation lessons

### Sprint 2.2 - AI Mentors (Week 4)
- [ ] Component 8: AIMentorService (Maya persona)
- [ ] Component 10: FIMLEducationalDataAdapter
- [ ] FIML narrative integration

## Contributing

See main [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](../../LICENSE)
