import Constants from 'expo-constants';

// Use localhost for development (Android Emulator uses 10.0.2.2)
// For physical device, replace with your machine's LAN IP
const localhost = 'http://10.0.2.2:8000';
const productionHost = 'https://api.fiml.finance';

export const API_BASE_URL = __DEV__ ? localhost : productionHost;
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');

export const ENDPOINTS = {
    BOT_MESSAGE: `${API_BASE_URL}/api/bot/message`,
    WS_STREAM: `${WS_BASE_URL}/ws/stream`,
    HEALTH: `${API_BASE_URL}/health`,
};
