# FIML Expo App Development Blueprint

**Version**: 2.0 (React Native Focus)
**Target Framework**: Expo (React Native + Web)
**Backend**: FIML Server (FastAPI)

## 1. Architecture Overview

The Expo app functions as a rich client for the FIML platform. It uses a **Thin Client** architecture where business logic (lessons, quizzes, gamification) resides on the server, while the app focuses on presentation, real-time data visualization, and user interaction.

```mermaid
graph TD
    User[Mobile User] -->|Navigation| Router[Expo Router]
    Router -->|Screen| Screen[React Component]
    
    subgraph "State Management"
        Screen -->|Read/Write| Store[Zustand (Session/Auth)]
        Screen -->|Fetch| Query[TanStack Query (Async Data)]
    end
    
    subgraph "Data Layer"
        Query -->|REST| API[FIML API Client]
        Screen -->|Stream| WS[WebSocket Hook]
    end
    
    API -->|HTTP| Server[FIML Server :8000]
    WS -->|WS| Server
```

## 2. Project Structure

We will use a standard Expo Router structure with feature-based organization.

```
app/
├── (auth)/                 # Authentication routes
│   ├── login.tsx
│   └── onboarding.tsx
├── (tabs)/                 # Main tab navigation
│   ├── _layout.tsx
│   ├── index.tsx           # Dashboard / Home
│   ├── learn.tsx           # Lesson Browser
│   ├── market.tsx          # Market Data
│   └── profile.tsx         # User Profile
├── lesson/
│   └── [id].tsx            # Lesson Viewer (Modal/Stack)
├── quiz/
│   └── [id].tsx            # Quiz Interface
└── _layout.tsx             # Root layout

components/
├── ui/                     # Reusable UI (Buttons, Cards)
├── market/                 # Market widgets (Charts, Tickers)
├── education/              # Lesson/Quiz components
└── chat/                   # AI Mentor Chat interface

hooks/
├── useAuth.ts              # Authentication logic
├── useMarketData.ts        # WebSocket integration
└── useBotInteraction.ts    # API wrapper for bot gateway

services/
├── api.ts                  # Axios instance
└── websocket.ts            # WebSocket manager
```

## 3. Core Technologies

*   **Framework**: Expo SDK 50+
*   **Navigation**: Expo Router v3
*   **Styling**: NativeWind (Tailwind CSS)
*   **State Management**:
    *   **Global**: Zustand (User session, Theme)
    *   **Server State**: TanStack Query (API caching)
*   **Charts**: `react-native-wagmi-charts` (High performance interactive charts)
*   **Markdown**: `react-native-markdown-display` (Lesson content)

## 4. API Interface Specification

### 4.1 Bot Gateway (`/api/bot/message`)

**Request Interface**:
```typescript
interface BotMessageRequest {
  user_id: string;
  platform: 'mobile_app';
  text: string;
  context?: {
    screen?: string;
    lesson_id?: string;
    selected_option?: string;
  };
}
```

**Response Interface**:
```typescript
interface BotMessageResponse {
  text: string;
  media?: string[];
  actions?: BotAction[];
  metadata?: {
    intent: string;
    confidence: number;
    [key: string]: any;
  };
}

interface BotAction {
  type: 'button' | 'link' | 'input';
  label: string;
  value: string;
  style?: 'primary' | 'secondary' | 'danger';
}
```

### 4.2 WebSocket Stream (`/ws/stream`)

**Subscription Message**:
```typescript
interface SubscriptionRequest {
  type: 'subscribe';
  stream_type: 'price' | 'ohlcv';
  symbols: string[];
  interval_ms?: number;
}
```

**Update Message**:
```typescript
interface PriceUpdate {
  type: 'price_update';
  symbol: string;
  price: number;
  change_24h: number;
  volume: number;
  timestamp: string;
}
```

## 5. Component Implementation Details

### 5.1 `ChatInterface` (AI Mentor)
*   **Purpose**: Main interface for interacting with Maya, Theo, and Zara.
*   **Implementation**:
    *   Uses `FlatList` (inverted) to display message history.
    *   `TextInput` for user queries.
    *   Integrates `useBotInteraction` hook to send messages to `/api/bot/message`.
    *   Renders markdown responses using `react-native-markdown-display`.

### 5.2 `LessonViewer`
*   **Purpose**: Renders educational content.
*   **Implementation**:
    *   Fetches lesson content via Bot Gateway (Intent: `lesson_request`).
    *   Parses the markdown response.
    *   Injects custom React components into the markdown stream for interactive elements (e.g., `<QuizButton />`, `<LiveChart symbol="AAPL" />`).

### 5.3 `MarketDashboard`
*   **Purpose**: Real-time market overview.
*   **Implementation**:
    *   Uses `useMarketData` hook to manage WebSocket connection.
    *   Maintains a local map of `symbol -> price` updates.
    *   Renders `CandlestickChart` from `react-native-wagmi-charts` for detailed views.
    *   Optimized re-renders using `React.memo` for individual ticker rows.

## 6. State Management Strategy

### 6.1 Zustand Store (`useStore`)
```typescript
interface AppState {
  user: User | null;
  theme: 'light' | 'dark';
  activeSessionId: string | null;
  setUser: (user: User) => void;
  logout: () => void;
}
```

### 6.2 React Query Hooks
```typescript
// useLesson.ts
export const useLesson = (lessonId: string) => {
  return useQuery({
    queryKey: ['lesson', lessonId],
    queryFn: () => api.post('/bot/message', { 
      text: `/lesson ${lessonId}`,
      context: { intent: 'fetch_content' }
    })
  });
};
```

## 7. Configuration

**`constants.ts`**:
```typescript
import Constants from 'expo-constants';

const localhost = 'http://192.168.1.x:8000'; // Replace with your local IP
const productionHost = 'https://api.fiml.finance';

export const API_BASE_URL = __DEV__ ? localhost : productionHost;
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
```

## 8. Development Workflow

1.  **Start Backend**: `docker-compose up` (Ensure port 8000 is exposed).
2.  **Start Expo**: `npx expo start`.
3.  **Connect**:
    *   **Simulator**: Use `localhost` (Android requires `10.0.2.2`).
    *   **Physical Device**: Use your machine's LAN IP (e.g., `192.168.1.5`).
4.  **Verify**:
    *   Check `/health` endpoint.
    *   Send a test message in the Chat Interface.
