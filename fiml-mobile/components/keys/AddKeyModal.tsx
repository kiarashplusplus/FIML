import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ActivityIndicator } from 'react-native';

interface AddKeyModalProps {
    visible: boolean;
    providerName: string;
    providerDisplayName: string;
    onClose: () => void;
    onSubmit: (providerName: string, apiKey: string, apiSecret?: string) => Promise<void>;
}

export default function AddKeyModal({ visible, providerName, providerDisplayName, onClose, onSubmit }: AddKeyModalProps) {
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const needsSecret = ['binance', 'coinbase', 'kraken'].includes(providerName.toLowerCase());

    const handleSubmit = async () => {
        if (!apiKey.trim()) {
            setError('API Key is required');
            return;
        }

        if (needsSecret && !apiSecret.trim()) {
            setError('API Secret is required for this provider');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            await onSubmit(providerName, apiKey, needsSecret ? apiSecret : undefined);
            // Reset form
            setApiKey('');
            setApiSecret('');
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add API key');
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        setApiKey('');
        setApiSecret('');
        setError('');
        onClose();
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={handleClose}
        >
            <View className="flex-1 justify-center items-center bg-black/80 p-4">
                <View className="bg-gray-800 rounded-2xl w-full max-w-md p-6">
                    <Text className="text-white text-2xl font-bold mb-4">
                        🔑 Add {providerDisplayName} Key
                    </Text>

                    <Text className="text-gray-400 text-sm mb-4">
                        Enter your API credentials securely. Your keys are encrypted and stored locally.
                    </Text>

                    {/* API Key Input */}
                    <View className="mb-4">
                        <Text className="text-gray-300 font-medium mb-2">API Key</Text>
                        <TextInput
                            className="bg-gray-700 text-white p-3 rounded-lg"
                            placeholder="Enter your API key"
                            placeholderTextColor="#6B7280"
                            value={apiKey}
                            onChangeText={setApiKey}
                            autoCapitalize="none"
                            autoCorrect={false}
                            secureTextEntry
                        />
                    </View>

                    {/* API Secret Input (if needed) */}
                    {needsSecret && (
                        <View className="mb-4">
                            <Text className="text-gray-300 font-medium mb-2">API Secret</Text>
                            <TextInput
                                className="bg-gray-700 text-white p-3 rounded-lg"
                                placeholder="Enter your API secret"
                                placeholderTextColor="#6B7280"
                                value={apiSecret}
                                onChangeText={setApiSecret}
                                autoCapitalize="none"
                                autoCorrect={false}
                                secureTextEntry
                            />
                        </View>
                    )}

                    {/* Error Message */}
                    {error && (
                        <View className="bg-red-500/20 p-3 rounded-lg mb-4">
                            <Text className="text-red-400 text-sm">{error}</Text>
                        </View>
                    )}

                    {/* Action Buttons */}
                    <View className="flex-row space-x-3">
                        <TouchableOpacity
                            onPress={handleClose}
                            disabled={isLoading}
                            className="flex-1 bg-gray-700 py-3 rounded-lg"
                        >
                            <Text className="text-white text-center font-bold">Cancel</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={handleSubmit}
                            disabled={isLoading}
                            className="flex-1 bg-blue-600 py-3 rounded-lg"
                        >
                            {isLoading ? (
                                <ActivityIndicator color="white" />
                            ) : (
                                <Text className="text-white text-center font-bold">Add Key</Text>
                            )}
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </Modal>
    );
}
