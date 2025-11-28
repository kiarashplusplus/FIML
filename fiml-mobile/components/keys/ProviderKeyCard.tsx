import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';

interface ProviderKeyCardProps {
    provider: {
        name: string;
        displayName: string;
        isConnected: boolean;
        description?: string;
    };
    onAdd: (providerName: string) => void;
    onTest: (providerName: string) => void;
    onRemove: (providerName: string) => void;
}

export default function ProviderKeyCard({ provider, onAdd, onTest, onRemove }: ProviderKeyCardProps) {
    const statusColor = provider.isConnected ? 'bg-green-600/20 border-green-600/50' : 'bg-gray-700/20 border-gray-600/50';
    const statusIcon = provider.isConnected ? '🟢' : '🔴';
    const statusText = provider.isConnected ? 'Connected' : 'Not Connected';

    return (
        <View className={`p-4 rounded-xl border ${statusColor} mb-3`}>
            <View className="flex-row items-center justify-between mb-2">
                <View className="flex-row items-center flex-1">
                    <Text className="text-xl mr-2">{statusIcon}</Text>
                    <View className="flex-1">
                        <Text className="text-white font-bold text-lg">{provider.displayName}</Text>
                        <Text className="text-gray-400 text-sm">{statusText}</Text>
                    </View>
                </View>
            </View>

            {provider.description && (
                <Text className="text-gray-400 text-xs mb-3">{provider.description}</Text>
            )}

            <View className="flex-row space-x-2">
                {provider.isConnected ? (
                    <>
                        <TouchableOpacity
                            onPress={() => onTest(provider.name)}
                            className="flex-1 bg-blue-600 py-2 px-3 rounded-lg"
                        >
                            <Text className="text-white text-center font-medium text-sm">Test</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={() => onRemove(provider.name)}
                            className="flex-1 bg-red-600/80 py-2 px-3 rounded-lg"
                        >
                            <Text className="text-white text-center font-medium text-sm">Remove</Text>
                        </TouchableOpacity>
                    </>
                ) : (
                    <TouchableOpacity
                        onPress={() => onAdd(provider.name)}
                        className="flex-1 bg-blue-600 py-2 px-3 rounded-lg"
                    >
                        <Text className="text-white text-center font-medium text-sm">Add Key</Text>
                    </TouchableOpacity>
                )}
            </View>
        </View>
    );
}
