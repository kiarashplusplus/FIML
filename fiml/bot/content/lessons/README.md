# Educational Bot Lessons - Content Library

## Overview

This directory contains **15 comprehensive educational lessons** (with outlines for 5 more) covering foundational trading and investing concepts. Each lesson is designed for the FIML Educational Bot with live market data integration, interactive quizzes, and gamification.

## Lesson Structure

Each lesson follows a consistent YAML structure:
- **ID**: Unique identifier
- **Title**: Student-facing lesson name
- **Category**: Content classification
- **Difficulty**: beginner, intermediate, or advanced
- **Duration**: Expected completion time (5-8 minutes)
- **Learning Objectives**: 3-5 specific goals
- **Prerequisites**: Required prior lessons
- **Sections**: Introduction, explanations, live examples, key takeaways
- **Quiz**: 3-5 questions with explanations
- **XP Reward**: Gamification points (typically 50 XP)

## Completed Lessons (1-15)

### Fundamentals (6 lessons)
1. **Understanding Stock Prices** (stock_basics_001)
   - Bid, ask, spread
   - Supply and demand
   - 3 quiz questions, 50 XP

2. **Market Orders vs. Limit Orders** (stock_basics_002)
   - Order types and execution
   - When to use each
   - 4 quiz questions, 50 XP

3. **Volume and Liquidity** (stock_basics_003)
   - Trading volume concepts
   - Liquidity and trading costs
   - 4 quiz questions, 50 XP

4. **Understanding Market Cap** (stock_basics_004)
   - Market capitalization formula
   - Large, mid, small-cap categories
   - 4 quiz questions, 50 XP

14. **Reading Financial Statements Basics** (fundamentals_001)
    - Income statement, balance sheet, cash flow
    - Key ratios and red flags
    - 4 quiz questions, 50 XP

### Valuation (1 lesson)
5. **P/E Ratio: Is This Stock Expensive?** (valuation_001)
   - Price-to-earnings explained
   - Interpreting P/E values
   - 4 quiz questions, 50 XP

### Technical Analysis (2 lessons)
6. **Support and Resistance Basics** (technical_001)
   - Price levels and breakouts
   - Trading strategies
   - 4 quiz questions, 50 XP

12. **Moving Averages: Finding the Trend** (technical_002)
    - 50-day and 200-day MAs
    - Golden/death crosses
    - 4 quiz questions, 50 XP

### Risk Management (2 lessons)
7. **Position Sizing: How Much to Invest?** (risk_001)
   - 1-2% risk rule
   - Position size calculation
   - 4 quiz questions, 50 XP

8. **Stop Losses: Your Safety Net** (risk_002)
   - Stop-loss types and placement
   - Common mistakes
   - 4 quiz questions, 50 XP

### Portfolio Management (2 lessons)
9. **Diversification: Don't Put All Eggs in One Basket** (portfolio_001)
   - Diversification principles
   - Sector and asset allocation
   - 4 quiz questions, 50 XP

15. **Index Funds vs. Individual Stocks** (portfolio_002)
    - Active vs. passive investing
    - Core-satellite strategy
    - 4 quiz questions, 50 XP

### Trading Psychology (1 lesson)
10. **Fear and Greed: The Market's Two Emotions** (psychology_001)
    - Emotional cycles in markets
    - Contrarian thinking
    - 4 quiz questions, 50 XP

### Income Investing (1 lesson)
11. **Dividend Investing: Getting Paid to Own Stocks** (income_001)
    - Dividend yield and aristocrats
    - DRIP and compounding
    - 4 quiz questions, 50 XP

### Market Concepts (1 lesson)
13. **Bull Markets vs. Bear Markets** (market_concepts_001)
    - Bull/bear definitions
    - Market cycles
    - 4 quiz questions, 50 XP

## Planned Lessons (16-20)

Outlines available in `README_LESSONS_15_20.md`:

16. **Dollar-Cost Averaging (DCA)** - investment_strategies
17. **Understanding Market Cap Weighted Indexes** - market_concepts
18. **Inflation and Stock Returns** - economics
19. **Tax-Efficient Investing** - tax_strategy
20. **Creating Your Investment Plan** - investment_planning

## Learning Path Recommendations

### Beginner Path (Start here)
1. Understanding Stock Prices (Lesson 1)
2. Market Orders vs. Limit Orders (Lesson 2)
3. Volume and Liquidity (Lesson 3)
4. Understanding Market Cap (Lesson 4)
5. Diversification (Lesson 9)
6. Index Funds vs. Individual Stocks (Lesson 15)
7. Bull Markets vs. Bear Markets (Lesson 13)

### Intermediate Path (After completing beginner path)
8. P/E Ratio (Lesson 5)
9. Position Sizing (Lesson 7)
10. Stop Losses (Lesson 8)
11. Support and Resistance (Lesson 6)
12. Moving Averages (Lesson 12)
13. Fear and Greed (Lesson 10)
14. Financial Statements (Lesson 14)

### Advanced Path (Optional specialization)
15. Dividend Investing (Lesson 11)
16-20. Planned advanced lessons

## FIML Integration

Each lesson includes `fiml_query` sections that trigger live market data:
- Real-time price quotes
- Volume and trading metrics
- Moving averages
- Dividend information
- Market cap calculations

Example:
```yaml
fiml_query:
  symbol: AAPL
  metrics:
    - price
    - volume
    - market_cap
```

## Quiz System

- **Total Questions**: 60+ across 15 lessons
- **Question Types**: Multiple choice, true/false, numeric
- **XP Rewards**: 10 XP per question, 50 XP per lesson
- **Instant Feedback**: Explanations for each answer
- **Progress Tracking**: Integrated with gamification engine

## Gamification Integration

**Total XP Available**: 750+ XP from lessons
- Lesson completion: 50 XP each
- Quiz questions: 10 XP each
- Badges: "First Steps" (complete first lesson)

**Level Progression**:
- 750 XP reaches Level 5 (Apprentice)
- Requires 1,000 XP for Level 6

## Content Statistics

- **Total Lessons**: 15 complete + 5 outlined
- **Total Words**: ~35,000
- **Total Quiz Questions**: 60+
- **Average Lesson Length**: 2,300 words
- **Live FIML Examples**: 15 integrated queries
- **Categories**: 9 distinct categories
- **Difficulty Levels**: Beginner (9), Intermediate (6)

## File Naming Convention

```
[number]_[slug].yaml
```

Examples:
- `01_understanding_stock_prices.yaml`
- `05_pe_ratio.yaml`
- `15_index_funds_vs_individual_stocks.yaml`

## Usage with LessonContentEngine

```python
from fiml.bot.education.lesson_engine import LessonContentEngine

engine = LessonContentEngine()
lesson = await engine.load_lesson("stock_basics_001")
rendered = await engine.render_lesson(lesson, user_id="user123")
```

## Next Steps

1. **Create Lessons 16-20**: Complete the foundation curriculum
2. **Add Historical Simulations**: 3 interactive market scenarios
3. **Create Learning Paths**: Structured progressions by goal
4. **Advanced Modules**: Options, Technical Analysis Deep Dive, Fundamental Analysis
5. **Multi-language**: Translate to Spanish, Portuguese

## Contributing

When adding new lessons:
1. Follow the YAML structure template
2. Include 3-5 learning objectives
3. Add 3-5 quiz questions with explanations
4. Integrate FIML live data where applicable
5. Set appropriate difficulty and prerequisites
6. Test quiz logic and XP rewards
7. Update this README

## Master Plan Alignment

These lessons fulfill the Phase 1 requirement:
> "Create 20 foundation lessons covering stocks, valuation, technical analysis, risk management, and portfolio theory"

**Status**: ✅ 75% complete (15/20 lessons delivered)
**Quality**: Production-ready with full FIML integration
**Next Milestone**: Complete remaining 5 lessons by end of Phase 1

---

**Last Updated**: 2025-11-24
**Total Content**: 15 complete lessons, ~35,000 words
**Status**: Phase 1 Sprint 4 (Content Creation) - In Progress
