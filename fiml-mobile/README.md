# FIML Mobile App

This is the Expo/React Native client for the FIML platform.

## Getting Started

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Start the App**:
    ```bash
    npx expo start
    ```

3.  **Run on Device/Simulator**:
    *   Press `a` for Android Emulator.
    *   Press `i` for iOS Simulator (macOS only).
    *   Scan the QR code with Expo Go on your physical device.

## Configuration

Update `constants.ts` to point to your FIML backend:

```typescript
// constants.ts
const localhost = 'http://YOUR_LOCAL_IP:8000'; 
```

## Features

*   **Chat Interface**: Talk to Maya, Theo, and Zara.
*   **Market Data**: Real-time price updates (Coming Soon).
*   **Lessons**: Interactive educational content (Coming Soon).
