import Constants from 'expo-constants';
import { Platform } from 'react-native';

const getBaseUrl = () => {
    if (__DEV__) {
        // Web always uses localhost
        if (Platform.OS === 'web') {
            return 'http://localhost:8000';
        }

        // Attempt to get the host IP from Expo constants (works for physical devices and some emulators)
        const debuggerHost = Constants.expoConfig?.hostUri;
        const localhost = debuggerHost?.split(':')[0];

        if (localhost) {
            return `http://${localhost}:8000`;
        }

        // Fallback for Android Emulator if hostUri is not available
        return 'http://10.0.2.2:8000';
    }
    return 'https://api.fiml.finance';
};

export const API_BASE_URL = getBaseUrl();
console.log('API_BASE_URL configured as:', API_BASE_URL);
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
