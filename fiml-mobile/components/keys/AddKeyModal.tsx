import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ActivityIndicator, Linking } from 'react-native';
import { useAuth } from '../../hooks/useAuth';
import keyManagementService from '../../services/keyManagement';
import type { AddKeyModalProps } from '../../types';

// UI timing constants
const SUCCESS_MODAL_DELAY_MS = 1500; // 1.5 seconds
const VALIDATION_DEBOUNCE_MS = 500;   // 0.5 seconds

export default function AddKeyModal({ visible, providerName, providerDisplayName, onClose, onSubmit }: AddKeyModalProps) {
    const { user } = useAuth();
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);
    const [error, setError] = useState('');

    // Format validation state
    const [isValidating, setIsValidating] = useState(false);
    const [formatValid, setFormatValid] = useState<boolean | null>(null);
    const [formatMessage, setFormatMessage] = useState('');

    const needsSecret = ['binance', 'coinbase', 'kraken'].includes(providerName.toLowerCase());

    // Debounced format validation
    useEffect(() => {
        if (!apiKey || apiKey.length === 0) {
            setFormatValid(null);
            setFormatMessage('');
            return;
        }

        setIsValidating(true);
        const timeoutId = setTimeout(async () => {
            if (user?.id) {
                const result = await keyManagementService.validateKeyFormat(
                    user.id,
                    providerName,
                    apiKey
                );
                setFormatValid(result.valid);
                setFormatMessage(result.message || '');
                setIsValidating(false);
            }
        }, VALIDATION_DEBOUNCE_MS);

        return () => {
            clearTimeout(timeoutId);
            setIsValidating(false);
        };
    }, [apiKey, providerName, user?.id]);

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

            // Show success state
            setShowSuccess(true);

            // Close after delay
            setTimeout(() => {
                setApiKey('');
                setApiSecret('');
                setShowSuccess(false);
                setIsLoading(false);
                onClose();
            }, SUCCESS_MODAL_DELAY_MS);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add API key');
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        if (!isLoading) {
            setApiKey('');
            setApiSecret('');
            setError('');
            setShowSuccess(false);
            onClose();
        }
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

                    {showSuccess ? (
                        <View className="items-center py-8">
                            <View className="bg-green-500/20 p-6 rounded-full mb-4">
                                <Text className="text-green-400 text-5xl">✓</Text>
                            </View>
                            <Text className="text-green-400 font-bold text-xl">Key Added!</Text>
                            <Text className="text-gray-400 mt-2">Closing...</Text>
                        </View>
                    ) : (
                        <>
                            <Text className="text-gray-400 text-sm mb-1">
                                Enter your API credentials securely. Your keys are encrypted and stored locally.
                            </Text>
                            <TouchableOpacity
                                onPress={() => Linking.openURL('https://kiarashplusplus.github.io/FIML/user-guide/api-keys/')}
                                className="mb-4"
                            >
                                <Text className="text-blue-400 text-sm underline">
                                    Need help finding your key?
                                </Text>
                            </TouchableOpacity>

                            {/* API Key Input */}
                            <View className="mb-4">
                                <Text className="text-gray-300 font-medium mb-2">API Key</Text>
                                <View className="relative">
                                    <TextInput
                                        className="bg-gray-700 text-white p-3 rounded-lg pr-12"
                                        placeholder="Enter your API key"
                                        placeholderTextColor="#6B7280"
                                        value={apiKey}
                                        onChangeText={setApiKey}
                                        autoCapitalize="none"
                                        autoCorrect={false}
                                        secureTextEntry
                                        editable={!isLoading}
                                    />
                                    {/* Format validation indicator */}
                                    {apiKey.length > 0 && (
                                        <View className="absolute right-3 top-3">
                                            {isValidating ? (
                                                <ActivityIndicator size="small" color="#9CA3AF" />
                                            ) : formatValid === true ? (
                                                <Text className="text-green-400 text-xl">✓</Text>
                                            ) : formatValid === false ? (
                                                <Text className="text-red-400 text-xl">✕</Text>
                                            ) : null}
                                        </View>
                                    )}
                                </View>

                                {/* Format feedback message */}
                                {formatMessage && apiKey.length > 0 && !isValidating && (
                                    <Text className={`text-xs mt-1 ${formatValid ? 'text-green-400' : 'text-red-400'}`}>
                                        {formatMessage}
                                    </Text>
                                )}
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
                                        editable={!isLoading}
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
                                    className={`flex-1 py-3 rounded-lg ${isLoading ? 'bg-blue-600/50' : 'bg-blue-600'}`}
                                >
                                    {isLoading ? (
                                        <ActivityIndicator color="white" />
                                    ) : (
                                        <Text className="text-white text-center font-bold">Add Key</Text>
                                    )}
                                </TouchableOpacity>
                            </View>
                        </>
                    )}
                </View>
            </View>
        </Modal>
    );
}
