import type { ProviderInfo } from './types';

/**
 * Comprehensive provider definitions for FIML Mobile
 * Synced with backend provider registry (17 providers total)
 */

export const PROVIDERS: Record<string, ProviderInfo> = {
    // ============================================================================
    // Free Tier Providers (No API Key Required)
    // ============================================================================

    yfinance: {
        name: 'yfinance',
        displayName: 'Yahoo Finance',
        description: 'Free stock and market data from Yahoo Finance',
        needsSecret: false,
        tier: 'free',
    },

    coingecko: {
        name: 'coingecko',
        displayName: 'CoinGecko',
        description: 'Free cryptocurrency market data and analytics',
        needsSecret: false,
        tier: 'free',
    },

    defillama: {
        name: 'defillama',
        displayName: 'DefiLlama',
        description: 'Free DeFi protocol analytics and TVL data',
        needsSecret: false,
        tier: 'free',
    },

    // ============================================================================
    // CCXT Crypto Exchanges (Public API - No Key Required for Market Data)
    // ============================================================================

    'ccxt-kraken': {
        name: 'ccxt-kraken',
        displayName: 'Kraken (CCXT)',
        description: 'Crypto exchange data via CCXT - reliable public API',
        needsSecret: false,
        tier: 'free',
    },

    'ccxt-kucoin': {
        name: 'ccxt-kucoin',
        displayName: 'KuCoin (CCXT)',
        description: 'Crypto exchange data via CCXT - wide token coverage',
        needsSecret: false,
        tier: 'free',
    },

    'ccxt-okx': {
        name: 'ccxt-okx',
        displayName: 'OKX (CCXT)',
        description: 'Crypto exchange data via CCXT - major exchange',
        needsSecret: false,
        tier: 'free',
    },

    'ccxt-bybit': {
        name: 'ccxt-bybit',
        displayName: 'Bybit (CCXT)',
        description: 'Crypto exchange data via CCXT - derivatives focused',
        needsSecret: false,
        tier: 'free',
    },

    'ccxt-gateio': {
        name: 'ccxt-gateio',
        displayName: 'Gate.io (CCXT)',
        description: 'Crypto exchange data via CCXT - extensive altcoin support',
        needsSecret: false,
        tier: 'free',
    },

    'ccxt-bitget': {
        name: 'ccxt-bitget',
        displayName: 'Bitget (CCXT)',
        description: 'Crypto exchange data via CCXT - growing exchange',
        needsSecret: false,
        tier: 'free',
    },

    // ============================================================================
    // Premium Tier Providers (API Key Required)
    // ============================================================================

    alpha_vantage: {
        name: 'alpha_vantage',
        displayName: 'Alpha Vantage',
        description: 'Stock market data, technical indicators, and fundamentals',
        needsSecret: false,
        tier: 'premium',
    },

    fmp: {
        name: 'fmp',
        displayName: 'Financial Modeling Prep',
        description: 'Comprehensive financial data and company fundamentals',
        needsSecret: false,
        tier: 'premium',
    },

    polygon: {
        name: 'polygon',
        displayName: 'Polygon.io',
        description: 'Real-time and historical market data',
        needsSecret: false,
        tier: 'premium',
    },

    finnhub: {
        name: 'finnhub',
        displayName: 'Finnhub',
        description: 'Stock market data, news, and company information',
        needsSecret: false,
        tier: 'premium',
    },

    twelvedata: {
        name: 'twelvedata',
        displayName: 'Twelve Data',
        description: 'Global market data for stocks, forex, and crypto',
        needsSecret: false,
        tier: 'premium',
    },

    tiingo: {
        name: 'tiingo',
        displayName: 'Tiingo',
        description: 'Financial data platform with news and fundamentals',
        needsSecret: false,
        tier: 'premium',
    },

    marketstack: {
        name: 'marketstack',
        displayName: 'Marketstack',
        description: 'Real-time and historical stock market data',
        needsSecret: false,
        tier: 'premium',
    },

    coinmarketcap: {
        name: 'coinmarketcap',
        displayName: 'CoinMarketCap',
        description: 'Cryptocurrency market data and rankings',
        needsSecret: false,
        tier: 'premium',
    },

    newsapi: {
        name: 'newsapi',
        displayName: 'NewsAPI',
        description: 'Financial news and market sentiment analysis',
        needsSecret: false,
        tier: 'premium',
    },

    fred: {
        name: 'fred',
        displayName: 'FRED',
        description: 'Federal Reserve Economic Data (Macro Indicators)',
        needsSecret: false,
        tier: 'free',
    },

    // ============================================================================
    // Enterprise Tier Providers
    // ============================================================================

    intrinio: {
        name: 'intrinio',
        displayName: 'Intrinio',
        description: 'Enterprise-grade financial data and analytics',
        needsSecret: false,
        tier: 'enterprise',
    },

    quandl: {
        name: 'quandl',
        displayName: 'Quandl',
        description: 'Alternative, economic, and macro data',
        needsSecret: false,
        tier: 'enterprise',
    },
};

/**
 * Get all providers as an array
 */
export const getAllProviders = (): ProviderInfo[] => {
    return Object.values(PROVIDERS);
};

/**
 * Get providers by tier
 */
export const getProvidersByTier = (tier: 'free' | 'premium' | 'enterprise'): ProviderInfo[] => {
    return getAllProviders().filter(p => p.tier === tier);
};

/**
 * Get a specific provider by name
 */
export const getProvider = (name: string): ProviderInfo | undefined => {
    return PROVIDERS[name];
};

/**
 * Total provider count
 */
export const TOTAL_PROVIDERS = Object.keys(PROVIDERS).length;
