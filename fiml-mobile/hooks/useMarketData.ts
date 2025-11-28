import { useEffect, useRef, useState } from 'react';
import { WS_BASE_URL } from '../constants';
import * as api from '../services/api';

interface PriceUpdate {
    type: 'price_update';
    symbol: string;
    price: number;
    change_24h: number;
    volume: number;
    timestamp: string;
}

export const useMarketData = (symbols: string[]) => {
    const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (!symbols.length) return;

        const connect = () => {
            ws.current = new WebSocket(`${WS_BASE_URL}/ws/stream`);

            ws.current.onopen = () => {
                setIsConnected(true);
                // Subscribe to symbols
                ws.current?.send(JSON.stringify({
                    type: 'subscribe',
                    stream_type: 'price',
                    symbols,
                }));
            };

            ws.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'price_update') {
                        setPrices((prev) => ({
                            ...prev,
                            [data.symbol]: data,
                        }));
                    }
                } catch (e) {
                    console.error('Failed to parse WS message', e);
                }
            };

            ws.current.onclose = () => {
                setIsConnected(false);
                // Reconnect after 5s
                setTimeout(connect, 5000);
            };

            ws.current.onerror = (e) => {
                console.error('WebSocket error', e);
            };
        };

        connect();

        return () => {
            ws.current?.close();
        };
    }, [JSON.stringify(symbols)]);

    const getHistory = async (symbol: string, timeframe: string = '1d') => {
        try {
            return await api.getHistoricalData(symbol, timeframe);
        } catch (e) {
            console.error('Failed to fetch history', e);
            return [];
        }
    };

    return { prices, isConnected, getHistory };
};
