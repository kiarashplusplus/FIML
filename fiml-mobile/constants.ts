import { Platform } from 'react-native';

const getLocalHost = () => {
    // Android Emulator requires 10.0.2.2 to access host machine
    if (Platform.OS === 'android') {
        return 'http://10.0.2.2:8000';
    }

    // iOS Simulator and Web can access host machine via localhost
    // Note: For physical devices, you must replace this with your LAN IP (e.g., http://192.168.1.x:8000)
    return 'http://localhost:8000';
};

const localhost = getLocalHost();
const productionHost = 'https://api.fiml.finance';

export const API_BASE_URL = __DEV__ ? localhost : productionHost;
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');

export const ENDPOINTS = {
    BOT_MESSAGE: `${API_BASE_URL}/api/bot/message`,
    WS_STREAM: `${WS_BASE_URL}/ws/stream`,
    HEALTH: `${API_BASE_URL}/health`,
};
