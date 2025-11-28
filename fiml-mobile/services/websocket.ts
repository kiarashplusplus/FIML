import useWebSocket, { ReadyState } from 'react-use-websocket';
import { WS_BASE_URL } from '../constants';
import { useState, useEffect, useCallback } from 'react';

export const useMarketStream = (symbols: string[] = []) => {
    const [prices, setPrices] = useState<Record<string, any>>({});

    const { sendMessage, lastMessage, readyState } = useWebSocket(WS_BASE_URL, {
        shouldReconnect: () => true,
        reconnectAttempts: 10,
        reconnectInterval: 3000,
    });

    // Handle incoming messages
    useEffect(() => {
        if (lastMessage !== null) {
            try {
                const data = JSON.parse(lastMessage.data);
                if (data.type === 'price_update') {
                    setPrices((prev) => ({
                        ...prev,
                        [data.symbol]: data,
                    }));
                }
            } catch (e) {
                console.error('Failed to parse WS message', e);
            }
        }
    }, [lastMessage]);

    // Subscribe to symbols
    const subscribe = useCallback((newSymbols: string[]) => {
        if (readyState === ReadyState.OPEN) {
            sendMessage(JSON.stringify({
                type: 'subscribe',
                stream_type: 'price',
                symbols: newSymbols,
                interval_ms: 1000,
            }));
        }
    }, [readyState, sendMessage]);

    // Auto-subscribe when symbols change
    useEffect(() => {
        if (symbols.length > 0 && readyState === ReadyState.OPEN) {
            subscribe(symbols);
        }
    }, [symbols, readyState, subscribe]);

    return {
        prices,
        readyState,
        subscribe,
    };
};
