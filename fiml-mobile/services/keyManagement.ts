import { API_BASE_URL } from '../constants';
import * as SecureStore from 'expo-secure-store';
import type { Provider, KeyManagementResponse, ValidationResponse } from '../types';

// Cache configuration
const CACHE_KEYS = {
    PROVIDER_STATUS: 'provider_status_cache',
    CACHE_TIMESTAMP: 'provider_status_timestamp',
} as const;

// Time constants (in milliseconds)
const TIME_CONSTANTS = {
    CACHE_DURATION_MS: 5 * 60 * 1000,      // 5 minutes
    REQUEST_TIMEOUT_MS: 10 * 1000,          // 10 seconds
    SUCCESS_MODAL_DELAY_MS: 1500,           // 1.5 seconds
    REMOVE_KEY_DELAY_MS: 1000,              // 1 second
} as const;

class KeyManagementService {
    private authTokenKey = 'auth_token';

    /**
     * Get authentication token from secure storage
     */
    private async getAuthToken(): Promise<string | null> {
        try {
            return await SecureStore.getItemAsync(this.authTokenKey);
        } catch (error) {
            console.error('Failed to get auth token:', error);
            return null;
        }
    }

    /**
     * Check if cached data is still valid
     */
    private async isCacheValid(): Promise<boolean> {
        try {
            const timestamp = await SecureStore.getItemAsync(CACHE_KEYS.CACHE_TIMESTAMP);
            if (!timestamp) return false;

            const cacheAge = Date.now() - parseInt(timestamp, 10);
            return cacheAge < TIME_CONSTANTS.CACHE_DURATION_MS;
        } catch {
            return false;
        }
    }

    /**
     * Get provider status from cache
     */
    private async getCachedStatus(): Promise<Provider[] | null> {
        try {
            const cached = await SecureStore.getItemAsync(CACHE_KEYS.PROVIDER_STATUS);
            if (!cached) return null;

            return JSON.parse(cached);
        } catch (error) {
            console.error('Failed to read cache:', error);
            return null;
        }
    }

    /**
     * Save provider status to cache
     */
    private async cacheStatus(providers: Provider[]): Promise<void> {
        try {
            await SecureStore.setItemAsync(
                CACHE_KEYS.PROVIDER_STATUS,
                JSON.stringify(providers)
            );
            await SecureStore.setItemAsync(
                CACHE_KEYS.CACHE_TIMESTAMP,
                Date.now().toString()
            );
        } catch (error) {
            console.error('Failed to cache provider status:', error);
        }
    }

    /**
     * Clear cached provider status
     */
    async clearCache(): Promise<void> {
        try {
            await SecureStore.deleteItemAsync(CACHE_KEYS.PROVIDER_STATUS);
            await SecureStore.deleteItemAsync(CACHE_KEYS.CACHE_TIMESTAMP);
        } catch (error) {
            console.error('Failed to clear cache:', error);
        }
    }

    /**
     * Get all provider status for a user
     * Uses cache when available and valid
     */
    async getProviderStatus(userId: string, forceRefresh: boolean = false): Promise<Provider[]> {
        // Check cache first (unless force refresh)
        if (!forceRefresh) {
            const isValid = await this.isCacheValid();
            if (isValid) {
                const cached = await this.getCachedStatus();
                if (cached) {
                    console.log('Using cached provider status');
                    return cached;
                }
            }
        }

        // Fetch from API
        try {
            const token = await this.getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                const providers = data.providers || [];

                // Cache the result
                await this.cacheStatus(providers);

                return providers;
            }
        } catch (error) {
            console.error('Failed to fetch provider status:', error);

            // On network error, try to return stale cache
            const cached = await this.getCachedStatus();
            if (cached) {
                console.log('Network error - using stale cache');
                return cached;
            }
        }

        // Fallback to default providers
        return this.getDefaultProviders();
    }

    /**
     * Validate API key format in real-time (without storing)
     */
    async validateKeyFormat(userId: string, provider: string, apiKey: string): Promise<ValidationResponse> {
        if (!apiKey || apiKey.length === 0) {
            return { valid: false, message: 'API key required' };
        }

        try {
            const token = await this.getAuthToken();
            const response = await fetch(
                `${API_BASE_URL}/api/user/${userId}/keys/${provider}/validate-format`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ api_key: apiKey }),
                }
            );

            if (response.ok) {
                const data = await response.json();
                return {
                    valid: data.valid,
                    message: data.message,
                    expected_pattern: data.expected_pattern,
                };
            }

            return { valid: false, message: 'Validation failed' };
        } catch (error) {
            console.error('Format validation error:', error);
            // On error, don't block the user
            return { valid: true, message: 'Unable to validate format' };
        }
    }

    /**
     * Get default provider list (offline fallback)
     */
    private getDefaultProviders(): Provider[] {

    /**
     * Add a new API key
     */
    async addKey(userId: string, provider: string, apiKey: string, apiSecret ?: string): Promise < KeyManagementResponse > {
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

                // Handle different HTTP status codes
                if(response.status === 201) {
            // Clear cache on successful addition
            await this.clearCache();

            const data = await response.json();
            return {
                success: true,
                message: data.message || 'API key added successfully',
            };
        }

        // Parse error response
        const errorData = await response.json();

        if (response.status === 400) {
            return {
                success: false,
                error: errorData.detail || 'Invalid provider or key format',
            };
        }

        if (response.status === 500) {
            return {
                success: false,
                error: 'Server error. Please try again later.',
            };
        }

        return {
            success: false,
            error: errorData.detail || 'Failed to add API key',
        };
    } catch(error) {
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Network error',
        };
    }
}

    /**
     * Test if an API key is valid
     */
    async testKey(userId: string, provider: string): Promise < KeyManagementResponse > {
    try {
        const token = await this.getAuthToken();
        const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys/${provider}/test`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        // Handle different HTTP status codes
        if(response.status === 200) {
    const data = await response.json();
    return {
        success: true,
        message: data.message || 'API key is valid',
    };
}

// Parse error response
const errorData = await response.json();

if (response.status === 404) {
    return {
        success: false,
        error: 'No API key found for this provider',
    };
}

if (response.status === 400) {
    return {
        success: false,
        error: errorData.detail || 'Key validation failed',
    };
}

if (response.status === 500) {
    return {
        success: false,
        error: 'Server error. Please try again later.',
    };
}

return {
    success: false,
    error: errorData.detail || 'Key test failed',
};
        } catch (error) {
    return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
    };
}
    }

    async removeKey(userId: string, provider: string): Promise < KeyManagementResponse > {
    try {
        const token = await this.getAuthToken();
        const response = await fetch(`${API_BASE_URL}/api/user/${userId}/keys/${provider}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        const data = await response.json();

        if(response.ok && data.success) {
    // Clear cache on successful removal
    await this.clearCache();

    return {
        success: true,
        message: data.message || 'API key removed successfully',
    };
}

return {
    success: false,
    error: data.error || 'Failed to remove API key',
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

// Re-export types for convenience
export type { Provider, KeyManagementResponse, ValidationResponse } from '../types';

export default new KeyManagementService();
