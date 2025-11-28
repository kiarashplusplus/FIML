import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, RefreshControl } from 'react-native';
import type { UsageStatsResponse } from '../../types';
import UsageProgressBar from './UsageProgressBar';

interface UsageStatsCardProps {
    stats: UsageStatsResponse | null;
    loading: boolean;
    onRefresh: () => void;
}

export default function UsageStatsCard({ stats, loading, onRefresh }: UsageStatsCardProps) {
    if (!stats || stats.stats.length === 0) {
        return null; // Hide if no usage data
    }

    return (
        <View className="bg-gray-800 rounded-xl p-4 mb-4 mx-4">
            {/* Header */}
            <View className="flex-row justify-between items-center mb-3">
                <Text className="text-white text-xl font-bold">
                    📊 API Usage
                </Text>
                <TouchableOpacity
                    onPress={onRefresh}
                    disabled={loading}
                    className="bg-gray-700 px-3 py-1 rounded-lg"
                >
                    <Text className="text-blue-400 text-sm">
                        {loading ? '...' : '🔄'}
                    </Text>
                </TouchableOpacity>
            </View>

            {/* Total calls today */}
            <View className="bg-gray-900 rounded-lg p-3 mb-4">
                <Text className="text-gray-400 text-sm mb-1">Today's Total</Text>
                <Text className="text-white text-2xl font-bold">
                    {stats.total_calls_today.toLocaleString()}
                </Text>
                <Text className="text-gray-500 text-xs">API calls</Text>
            </View>

            {/* Warning banner */}
            {stats.has_warnings && (
                <View className="bg-orange-500/20 border border-orange-500/40 p-3 rounded-lg mb-4">
                    <Text className="text-orange-400 font-medium">
                        ⚠️ Approaching Quota Limits
                    </Text>
                    <Text className="text-orange-300 text-xs mt-1">
                        Some providers are at 80% or higher usage
                    </Text>
                </View>
            )}

            {/* Provider usage bars */}
            <View>
                <Text className="text-gray-400 text-sm mb-2 font-medium">
                    Per Provider Usage
                </Text>
                {stats.stats.map((stat) => (
                    <UsageProgressBar key={stat.provider} stat={stat} />
                ))}
            </View>

            {/* Last updated */}
            <Text className="text-gray-500 text-xs mt-3 text-center">
                Updated {new Date(stats.timestamp).toLocaleTimeString()}
            </Text>
        </View>
    );
}
