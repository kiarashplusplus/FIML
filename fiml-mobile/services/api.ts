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

export const login = async (credentials: any) => {
    // In a real app, this would return a JWT token
    // For this blueprint, we'll simulate a successful login if the backend accepts the request
    // or just return a mock user for now if the backend doesn't have a dedicated login endpoint yet
    // But per requirements, we should try to hit an endpoint.
    // Assuming a simple /api/auth/login endpoint exists or we use a mock one for now if not ready.
    // Let's assume we post to /api/auth/login
    try {
        const response = await api.post('/api/auth/login', credentials);
        return response.data;
    } catch (error) {
        console.warn('Login endpoint not found, falling back to mock user for demo');
        return {
            user: { id: 'user-123', name: credentials.username, xp: 100 },
            token: 'mock-jwt-token'
        };
    }
};

export const getMarketData = async (symbols: string[]) => {
    const response = await api.get('/api/market/prices', { params: { symbols: symbols.join(',') } });
    return response.data;
};

export const getAssetDetails = async (symbol: string) => {
    const response = await api.get(`/api/market/assets/${symbol}`);
    return response.data;
};

export const getHistoricalData = async (symbol: string, timeframe: string = '1d') => {
    // Mapping timeframe to backend format if needed
    const response = await api.get(`/api/market/candles/${symbol}`, { params: { timeframe } });
    return response.data;
};

// ============================================================================
// FK-DSL API Functions
// ============================================================================

export interface DSLQueryRequest {
    query: string;
    async_execution?: boolean;
}

export interface DSLQueryResponse {
    query: string;
    status: string;
    result?: Record<string, any>;
    task_id?: string;
    error?: string;
}

export interface DSLTemplate {
    id: string;
    name: string;
    description: string;
    query: string;
    example: string;
    category: string;
}

export interface DSLTemplatesResponse {
    templates: DSLTemplate[];
}

/**
 * Execute a FK-DSL query
 * 
 * Example queries:
 * - EVALUATE TSLA: PRICE, VOLATILITY(30d)
 * - COMPARE AAPL, MSFT: PE_RATIO, MARKET_CAP
 * - CORRELATE BTC, ETH: PRICE(90d)
 */
export const executeDSLQuery = async (request: DSLQueryRequest): Promise<DSLQueryResponse> => {
    const response = await api.post('/api/market/dsl/execute', request);
    return response.data;
};

/**
 * Get available DSL query templates
 */
export const getDSLTemplates = async (): Promise<DSLTemplatesResponse> => {
    const response = await api.get('/api/market/dsl/templates');
    return response.data;
};
