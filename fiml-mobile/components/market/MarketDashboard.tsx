import React from 'react';
import { View, Text, ScrollView } from 'react-native';
import { CandlestickChart } from 'react-native-wagmi-charts';
import { Line, Rect } from 'react-native-svg';
import { useMarketData } from '../../hooks/useMarketData';

const MarketDashboard = () => {
    const symbols = ['BTC', 'ETH', 'AAPL', 'TSLA'];
    const { prices, isConnected, getHistory } = useMarketData(symbols);
    const [chartsData, setChartsData] = React.useState<Record<string, any[]>>({});

    React.useEffect(() => {
        const fetchHistory = async () => {
            const newChartsData: Record<string, any[]> = {};
            for (const symbol of symbols) {
                const response = await getHistory(symbol, '1d');
                if (response && response.candles && response.candles.length > 0) {
                    newChartsData[symbol] = response.candles;
                }
            }
            setChartsData(newChartsData);
        };
        fetchHistory();
    }, [isConnected]); // Re-fetch when connected or just once on mount

    return (
        <ScrollView className="flex-1 bg-gray-900 p-4">
            <Text className="text-2xl font-bold text-white mb-4">Market Dashboard</Text>

            {!isConnected && (
                <View className="bg-yellow-500/20 p-2 rounded mb-4">
                    <Text className="text-yellow-500 text-center">Connecting to market data...</Text>
                </View>
            )}

            <View className="space-y-4">
                {symbols.map((symbol) => {
                    const data = prices[symbol];
                    return (
                        <View key={symbol} className="bg-gray-800 p-4 rounded-xl">
                            <View className="flex-row justify-between items-center mb-2">
                                <Text className="text-xl font-bold text-white">{symbol}</Text>
                                <View>
                                    <Text className="text-white text-right text-lg">
                                        ${data?.price?.toFixed(2) || '---'}
                                    </Text>
                                    <Text className={`text-right ${data?.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                        {data?.change_24h > 0 ? '+' : ''}{data?.change_24h?.toFixed(2)}%
                                    </Text>
                                </View>
                            </View>

                            {/* Simple chart visualization */}
                            <CandlestickChart.Provider data={chartsData[symbol] || []}>
                                <CandlestickChart height={150}>
                                    <CandlestickChart.Candles
                                        renderRect={({ useAnimations, ...props }) => <Rect {...props} />}
                                        renderLine={({ useAnimations, ...props }) => <Line {...props} />}
                                    />
                                </CandlestickChart>
                            </CandlestickChart.Provider>
                        </View>
                    );
                })}
            </View>
        </ScrollView>
    );
};

export default MarketDashboard;
