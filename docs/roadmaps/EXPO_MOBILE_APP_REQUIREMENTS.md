# FIML Expo Mobile App Requirements

**Version**: 1.0
**Status**: DRAFT
**Target Platform**: iOS & Android (via Expo / React Native)

## 1. Executive Summary
The FIML Mobile App is a native mobile interface for the Unified Educational Bot platform. It leverages the existing FIML backend (Unified Bot Gateway) to deliver an immersive, interactive financial education experience. Unlike the text-based Telegram bot, the mobile app offers rich visualizations, real-time charting, and a gamified learning environment.

## 2. Core Objectives
- **Unified Experience**: Seamlessly sync progress with the Telegram bot.
- **Rich Interaction**: Use native UI for charts, quizzes, and lesson navigation.
- **Real-Time Data**: Low-latency market data streaming via WebSockets.
- **BYOK First**: Secure, client-side key management for user API keys.

## 3. Feature Requirements

### 3.1 Authentication & Onboarding
- **Login/Signup**: Email/Password or Social Login (Google/Apple).
- **Device Sync**: Sync user ID with Telegram account (via deep link or code).
- **BYOK Setup**:
    - Interactive wizard to add API keys (Alpha Vantage, Finnhub, etc.).
    - Client-side validation of keys.
    - Secure storage using `expo-secure-store`.

### 3.2 Educational Module
- **Lesson Browser**:
    - Categorized list (Basics, Advanced, Crypto).
    - Progress indicators (progress bars, checkmarks).
- **Lesson Viewer**:
    - Rich text rendering (Markdown support).
    - Embedded interactive charts (e.g., "See how volume affects price").
    - "Next/Previous" navigation.
- **Quiz Interface**:
    - Native UI for Multiple Choice, True/False, Numeric input.
    - Immediate feedback with animations.
    - XP reward animations.

### 3.3 Market Data & Tools
- **Real-Time Dashboard**:
    - Watchlist with live prices (WebSocket).
    - Sparkline charts for quick trends.
- **Asset Details**:
    - Candlestick charts (using `react-native-wagmi-charts` or similar).
    - Key metrics (P/E, Market Cap, Volume).
    - AI-generated summary (via Narrative Engine).
- **FK-DSL Builder**:
    - Visual query builder (drag-and-drop or dropdowns) for FK-DSL.
    - "Run Query" button with formatted results.

### 3.4 AI Mentor Chat
- **Chat Interface**:
    - WhatsApp-style chat UI.
    - Persona selection (Maya, Theo, Zara).
    - Streaming responses (typing indicators).
    - Context-aware suggestions chips.

### 3.5 Gamification
- **User Profile**: Avatar, Level, Total XP.
- **Badges Gallery**: Grid view of earned and locked badges.
- **Streak Calendar**: Visual calendar of daily activity.
- **Leaderboard**: Global and friends ranking.

## 4. Technical Architecture

### 4.1 Tech Stack
- **Framework**: Expo (React Native)
- **Language**: TypeScript
- **State Management**: React Query (TanStack Query) + Zustand
- **Navigation**: Expo Router
- **Styling**: NativeWind (Tailwind CSS for React Native)
- **Charts**: `react-native-gifted-charts` or `victory-native`
- **Storage**: `expo-secure-store` (API Keys), `AsyncStorage` (Cache)

### 4.2 Backend Integration
- **API**: Connects to `UnifiedBotGateway` (FastAPI).
- **Protocol**: REST for CRUD, WebSocket for market data/chat.
- **Auth**: JWT-based authentication.

## 5. Roadmap

### Phase 1: MVP (Month 1-2)
- Authentication & Profile
- Lesson Viewer & Quizzes
- Basic Market Data (List view)
- AI Chat (Text only)

### Phase 2: Enhanced UI (Month 3)
- Interactive Charts
- FK-DSL Visual Builder
- Gamification Animations

### Phase 3: Social & Pro (Month 4+)
- Leaderboards
- Push Notifications (Streaks, Market Alerts)
- Pro Features (Multi-key support)
