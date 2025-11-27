# Educational Bot Quick Reference
## TL;DR for the Unified Educational Bot Master Plan

**Full Plan:** [UNIFIED_EDUCATIONAL_BOT_MASTER_PLAN.md](./UNIFIED_EDUCATIONAL_BOT_MASTER_PLAN.md)

---

## Overview

**What:** Multi-platform educational trading bot (Telegram → Web → WhatsApp)  
**Powered By:** FIML's data arbitration + MCP + narrative generation  
**Unique Angle:** BYOK (Bring Your Own Key) model - users provide their own API keys  
**Goal:** Teach trading/investing with real market data, no financial advice

---

## BYOK Model Benefits

✅ **Compliance:** Users access data through their own accounts  
✅ **Cost-Efficient:** No enterprise data redistribution  
✅ **Flexible:** Free tier (Yahoo) or premium providers (user choice)  
✅ **Scalable:** Each user's data costs are their own

---

## 11 Core Components

| # | Component | Purpose | Lines | AI Prompt |
|---|-----------|---------|-------|-----------|
| 1 | UserKeyOnboardingService | Collect & store user API keys | 400 | Telegram conversation flow for key collection with validation |
| 2 | FIMLProviderConfigurator | Configure FIML per-user | 300 | Per-user provider routing with fallback |
| 3 | UnifiedBotGateway | Message router for all platforms | 600 | Platform-agnostic message handling + intent classification |
| 4 | TelegramBotAdapter | Telegram bot integration | 500 | Commands, keyboards, media, webhooks |
| 5 | WebInterfaceAdapter | Web chat UI | 800 | Next.js + Socket.IO real-time chat |
| 6 | LessonContentEngine | Render lessons with live data | 450 | YAML parser + FIML data integration |
| 7 | QuizSystem | Multi-type quiz engine | 350 | Questions, validation, scoring, adaptive |
| 8 | AIMentorService | AI mentor personas (Maya, Theo, Zara) | 400 | Context-aware educational Q&A |
| 9 | GamificationEngine | XP, levels, streaks, badges | 300 | Progression system |
| 10 | FIMLEducationalDataAdapter | Format market data educationally | 350 | Beginner-friendly data interpretation |
| 11 | EducationalComplianceFilter | Block advice, add disclaimers | 400 | Pattern detection + content rewriting |

**Total:** ~4,850 lines

---

## Implementation Phases

### Phase 1: MVP - Telegram Bot (Weeks 1-8)

**Week 1-2:** BYOK + Bot Gateway Core  
- Components 1-4
- Foundation: key management, message routing

**Week 3-4:** Educational Content  
- Components 6-8, 10
- Lessons, quizzes, AI mentor, FIML data

**Week 5-6:** Gamification + Compliance  
- Components 9, 11
- XP system, safety filters

**Week 7-8:** Content + Launch  
- 20 foundation lessons
- 3 historical simulations
- Beta testing, launch

### Phase 2: Web Interface (Weeks 9-12)

- Component 5 (Web adapter)
- Next.js chat UI
- WebSocket real-time
- 20 more lessons

### Phase 3: WhatsApp + Scale (Weeks 13-16)

- WhatsApp adapter
- Multi-platform sync
- Advanced modules
- Multi-language

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot Gateway | Python 3.11+ FastAPI |
| Telegram | python-telegram-bot |
| Web Frontend | Next.js 14 + React |
| WhatsApp | whatsapp-cloud-api |
| Data Layer | FIML MCP Server |
| AI/LLM | Azure OpenAI (via FIML) |
| Session | Redis + PostgreSQL |
| Keys | AWS Secrets Manager |
| Deploy | Docker + K8s |

---

## Key Features

### For Users

- 📚 **Interactive Lessons** with real market data
- 🎓 **AI Mentors** (Maya, Theo, Zara)
- 🎮 **Gamification** (XP, streaks, badges)
- 📊 **Live Market Data** via FIML
- 🏆 **Historical Simulations** (Flash Crash, GME, etc.)
- 🔐 **BYOK** - use your own API keys

### For Platform

- 🌐 **Multi-Platform** (Telegram, Web, WhatsApp)
- 🛡️ **Compliance-First** (no advice, only education)
- 💰 **Cost-Efficient** (user-provided data keys)
- 📈 **Scalable** (costs scale with users)
- 🔧 **Extensible** (FIML provider system)

---

## Architecture Layers

```
┌────────────────────────────────────┐
│   Telegram | Web | WhatsApp       │ ← Platform Interfaces
└────────────────────────────────────┘
              ↓
┌────────────────────────────────────┐
│   Unified Bot Gateway              │ ← Message Router
└────────────────────────────────────┘
              ↓
┌────────────────────────────────────┐
│   Educational Orchestration        │ ← Lessons, Quizzes, AI
└────────────────────────────────────┘
              ↓
┌────────────────────────────────────┐
│   FIML Integration Layer           │ ← Data + Compliance
└────────────────────────────────────┘
              ↓
┌────────────────────────────────────┐
│   User's API Keys → Providers      │ ← BYOK Model
└────────────────────────────────────┘
```

---

## Success Metrics

### Learning
- Lesson Completion: **>70%**
- Quiz Accuracy: **>65%**
- 7-Day Retention: **>40%**

### Engagement
- Session Duration: **>12 min**
- AI Mentor Usage: **>50% weekly**
- Daily Active Users: **+10% MoM**

### Business
- Free → Pro Conversion: **>15%**
- LTV: **>$150**
- FIML Cost/MAU: **<$2**

---

## Cost Structure

### Per-User Monthly Costs

| Tier | Infrastructure | Margin |
|------|---------------|--------|
| Free (70%) | $2.00 | -$2.00 |
| Pro (25%) | $6.00 | +$9.00 |
| Premium (5%) | $8.00 | +$27.00 |

**Break-Even:** 15% conversion to Pro

---

## Sample User Flow

```
User: /start
Bot: Welcome! I'm your trading education bot.
     Let's set up your data access.
     
     Choose:
     1️⃣ Free (Yahoo Finance only)
     2️⃣ Pro (Add your own API keys)

User: 2
Bot: Great! Which provider do you have?
     1. Alpha Vantage (free tier available)
     2. Polygon.io (real-time)

User: 1
Bot: Get your free key: https://...
     Paste it here:

User: [paste key]
Bot: ✓ Validated! Free tier (5 req/min)
     
     You're ready to learn! 🎓
     /lesson - Start learning
```

---

## AI Agent Prompt Pattern

Each component has a detailed prompt following this pattern:

```
Build a [ComponentName] that [purpose].

**Context:** [Why this component exists]

**Requirements:**
1. Feature 1 with specifics
2. Feature 2 with specifics
...

**Tech Stack:** [Technologies to use]

**Code Structure:**
```python
class ComponentName:
    # Sample structure
```

**Acceptance Criteria:**
- ✅ Criterion 1
- ✅ Criterion 2

**Example Usage:**
[Code example]
```

**Full prompts:** See main plan document

---

## Next Steps

1. ✅ **Review master plan** ← You are here
2. Set up dev environment
3. Begin Sprint 1.1 (Components 1-2)
4. Build BYOK foundation
5. Iterate to MVP

---

## Quick Links

- 📄 [Full Master Plan](./UNIFIED_EDUCATIONAL_BOT_MASTER_PLAN.md)
- 📘 [FIML Blueprint](../../project/blueprint.md)
- 📚 [Full Use Case](../../examples/trading-bot.md)
- 🏠 [Main Documentation](../../index.md)

---

**For Questions:** GitHub Issues or Discord  
**Status:** Planning Phase  
**Version:** 1.0
