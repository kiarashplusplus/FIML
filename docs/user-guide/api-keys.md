# Getting API Keys

FIML aggregates financial data from over 16 different providers to ensure high availability, accuracy, and comprehensive market coverage. While some providers are completely free and require no configuration, others require an API key to access their data.

This guide explains how to obtain API keys for the supported providers and how to configure them in FIML.

## Free Providers (No Key Required)

These providers work out of the box without any configuration.

*   **Yahoo Finance**: Provides global equities, ETFs, and indices.
*   **CoinGecko**: Provides comprehensive cryptocurrency market data.
*   **DefiLlama**: Provides DeFi protocols, TVL, and stablecoin data.
*   **CCXT**: Provides public market data from hundreds of crypto exchanges.

## Freemium Providers (Key Required)

These providers offer a free tier that requires registration to obtain an API key. We recommend signing up for as many as possible to maximize FIML's reliability through its arbitration engine.

### 1. Alpha Vantage
*   **Best for**: Technical indicators, forex, US stocks.
*   **Free Tier**: 5 API calls per minute, 500 calls per day.
*   **Get Key**: [Claim your free API key](https://www.alphavantage.co/support/#api-key)

### 2. Financial Modeling Prep (FMP)
*   **Best for**: Fundamental data, financial statements.
*   **Free Tier**: 250 requests per day.
*   **Get Key**: [Sign up for free](https://financialmodelingprep.com/developer/docs)

### 3. Polygon.io
*   **Best for**: Real-time US stocks, options, crypto.
*   **Free Tier**: 5 API calls per minute.
*   **Get Key**: [Create an account](https://polygon.io/)

### 4. Finnhub
*   **Best for**: Global market data, earnings, economic calendar.
*   **Free Tier**: 60 API calls per minute.
*   **Get Key**: [Get free API key](https://finnhub.io/register)

### 5. Twelve Data
*   **Best for**: Real-time global stocks, forex, crypto.
*   **Free Tier**: 8 API calls per minute, 800 per day.
*   **Get Key**: [Sign up](https://twelvedata.com/pricing)

### 6. Tiingo
*   **Best for**: High-quality end-of-day data, news.
*   **Free Tier**: 500 symbols per month, 50 requests per hour.
*   **Get Key**: [Register](https://www.tiingo.com/)

### 7. NewsAPI
*   **Best for**: Global financial news and sentiment analysis.
*   **Free Tier**: 100 requests per day (for development).
*   **Get Key**: [Get API key](https://newsapi.org/register)

### 8. Marketstack
*   **Best for**: Global stock market data.
*   **Free Tier**: 100 requests per month.
*   **Get Key**: [Sign up](https://marketstack.com/product)

### 9. CoinMarketCap
*   **Best for**: Crypto rankings, market cap data.
*   **Free Tier**: 333 requests per day.
*   **Get Key**: [Get API key](https://coinmarketcap.com/api/)

### 10. Quandl (Nasdaq Data Link)
*   **Best for**: Alternative and historical data.
*   **Free Tier**: 50 calls per day.
*   **Get Key**: [Sign up](https://data.nasdaq.com/sign-up)

## Configuration

Once you have your API keys, you can configure them in FIML in two ways:

### Option 1: FIML Mobile App (Recommended)

If you are using the FIML mobile app:

1.  Navigate to **Settings**.
2.  Select **Provider Management** or **API Keys**.
3.  Tap on the provider you want to configure.
4.  Paste your API key and tap **Save**.
5.  The app will validate the key and enable the provider.

### Option 2: Backend Configuration (.env)

If you are running the FIML backend server directly, add your keys to the `.env` file in the project root:

```env
# Core Providers
ALPHA_VANTAGE_API_KEY=your_key_here
FMP_API_KEY=your_key_here
NEWSAPI_API_KEY=your_key_here

# Additional Providers
POLYGON_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
TWELVEDATA_API_KEY=your_key_here
TIINGO_API_KEY=your_key_here
INTRINIO_API_KEY=your_key_here
MARKETSTACK_API_KEY=your_key_here
COINMARKETCAP_API_KEY=your_key_here
QUANDL_API_KEY=your_key_here
```

Restart the server for the changes to take effect.
