import axios from 'axios';
import { API_BASE_URL } from '../constants';

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface BotMessageRequest {
    user_id: string;
    platform: 'mobile_app';
    text: string;
    context?: Record<string, any>;
}

export interface BotMessageResponse {
    text: string;
    media?: string[];
    actions?: any[];
    metadata?: {
        intent: string;
        confidence: number;
        [key: string]: any;
    };
}

export const sendMessage = async (request: BotMessageRequest): Promise<BotMessageResponse> => {
    const response = await api.post('/api/bot/message', request);
    return response.data;
};
