import { API_BASE_URL } from '../constants';
import * as SecureStore from 'expo-secure-store';

export interface Provider {
    name: string;
    displayName: string;
    isConnected: boolean;
    description?: string;
}

export interface KeyManagementResponse {
    success: boolean;
    message?: string;
    error?: string;
}

class KeyManagementService {
    private async getAuthToken(): Promise<string | null> {
        return await SecureStore.getItemAsync('authToken');
    }

    async getProviderStatus(userId: string): Promise<Provider[]> {
        try {
            const token = await this.getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Failed to fetch provider status');
            }

            const data = await response.json();
            return data.providers || [];
        } catch (error) {
            console.error('Error fetching provider status:', error);
            // Return default providers if API fails
            return this.getDefaultProviders();
        }
    }

    async addKey(userId: string, provider: string, apiKey: string, apiSecret?: string): Promise<KeyManagementResponse> {
        try {
            const token = await this.getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    provider,
                    api_key: apiKey,
                    api_secret: apiSecret,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || 'Failed to add API key',
                };
            }

            return {
                success: true,
                message: data.message || 'API key added successfully',
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async testKey(userId: string, provider: string): Promise<KeyManagementResponse> {
        try {
            const token = await this.getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys/${provider}/test`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || 'Key test failed',
                };
            }

            return {
                success: true,
                message: data.message || 'API key is valid',
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async removeKey(userId: string, provider: string): Promise<KeyManagementResponse> {
        try {
            const token = await this.getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys/${provider}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || 'Failed to remove API key',
                };
            }

            return {
                success: true,
                message: data.message || 'API key removed successfully',
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    private getDefaultProviders(): Provider[] {
        return [
            {
                name: 'binance',
                displayName: 'Binance',
                isConnected: false,
                description: 'Crypto trading data and market information',
            },
            {
                name: 'coinbase',
                displayName: 'Coinbase',
                isConnected: false,
                description: 'Cryptocurrency exchange integration',
            },
            {
                name: 'alphavantage',
                displayName: 'Alpha Vantage',
                isConnected: false,
                description: 'Stock market data and financial indicators',
            },
            {
                name: 'yfinance',
                displayName: 'Yahoo Finance',
                isConnected: false,
                description: 'Free stock and market data (no key required)',
            },
        ];
    }
}

export default new KeyManagementService();
