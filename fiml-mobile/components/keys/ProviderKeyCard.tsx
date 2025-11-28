import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';

interface Provider {
    name: string;
    displayName: string;
    isConnected: boolean;
    description?: string;
}

interface ProviderKeyCardProps {
    provider: Provider;
    onAdd: (providerName: string) => void;
    onTest: (providerName: string) => Promise<void>;
    onRemove: (providerName: string) => void;
}

export default function ProviderKeyCard({ provider, onAdd, onTest, onRemove }: ProviderKeyCardProps) {
    const [testingKey, setTestingKey] = useState(false);
    const [removingKey, setRemovingKey] = useState(false);

    const handleTest = async () => {
        setTestingKey(true);
        try {
            await onTest(provider.name);
        } finally {
            setTestingKey(false);
        }
    };

    const handleRemove = () => {
        if (removingKey) return;

        Alert.alert(
            'Remove API Key',
            `Are you sure you want to remove the ${provider.displayName} API key?`,
            [
                {
                    text: 'Cancel',
                    style: 'cancel'
                },
                {
                    text: 'Remove',
                    style: 'destructive',
                    onPress: () => {
                        setRemovingKey(true);
                        onRemove(provider.name);
                        setTimeout(() => setRemovingKey(false), 1000);
                    }
                }
            ]
        );
    };

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
                    <View className="flex-row mt-3 space-x-2">
                        <TouchableOpacity
                            onPress={handleTest}
                            disabled={testingKey || removingKey}
                            className={`flex-1 py-2 px-3 rounded-lg ${testingKey || removingKey ? 'bg-blue-600/50' : 'bg-blue-600'}`}
                        >
                            {testingKey ? (
                                <ActivityIndicator color="white" size="small" />
                            ) : (
                                <Text className="text-white text-center font-medium text-sm">Test</Text>
                            )}
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={handleRemove}
                            disabled={testingKey || removingKey}
                            className={`flex-1 py-2 px-3 rounded-lg ${testingKey || removingKey ? 'bg-red-600/50' : 'bg-red-600'}`}
                        >
                            {removingKey ? (
                                <ActivityIndicator color="white" size="small" />
                            ) : (
                                <Text className="text-white text-center font-medium text-sm">Remove</Text>
                            )}
                        </TouchableOpacity>
                    </View>
                ) : (
                    <TouchableOpacity
                        onPress={() => onAdd(provider.name)}
                        className="mt-3 bg-green-600 py-2 px-4 rounded-lg"
                    >
                        <Text className="text-white text-center font-medium">Add Key</Text>
                    </TouchableOpacity>
                )}
            </View>
        </View>
    );
}
