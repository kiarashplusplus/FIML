import React from 'react';
import { View, Text } from 'react-native';
import type { UsageStats } from '../../types';

interface UsageProgressBarProps {
    stat: UsageStats;
}

export default function UsageProgressBar({ stat }: UsageProgressBarProps) {
    // Determine color based on warning status
    const isInfinite = stat.daily_limit === Infinity || stat.daily_limit > 1000000;
    const color = stat.warning ? 'bg-orange-500' : 'bg-blue-500';
    const textColor = stat.warning ? 'text-orange-400' : 'text-blue-400';

    // Format limit display
    const limitDisplay = isInfinite ? '∞' : stat.daily_limit.toString();

    return (
        <View className="mb-3">
            <View className="flex-row justify-between mb-1">
                <Text className="text-gray-300 capitalize">{stat.provider}</Text>
                <Text className="text-gray-400 text-sm">
                    {stat.daily_usage} / {limitDisplay}
                </Text>
            </View>

            {/* Progress bar */}
            <View className="bg-gray-700 h-2 rounded-full overflow-hidden">
                <View
                    className={`${color} h-full`}
                    style={{ width: `${Math.min(stat.daily_percentage, 100)}%` }}
                />
            </View>

            {/* Warning message */}
            {stat.warning && !isInfinite && (
                <Text className={`${textColor} text-xs mt-1`}>
                    ⚠️ {stat.daily_percentage.toFixed(0)}% of daily limit
                </Text>
            )}

            {/* Tier badge */}
            {stat.tier && (
                <Text className="text-gray-500 text-xs mt-1">
                    {stat.tier} tier
                </Text>
            )}
        </View>
    );
}
