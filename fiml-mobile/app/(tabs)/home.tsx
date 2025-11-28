import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Alert, RefreshControl } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../hooks/useAuth';
import { useOnboarding } from '../../hooks/useOnboarding';
import ProviderKeyCard from '../../components/keys/ProviderKeyCard';
import AddKeyModal from '../../components/keys/AddKeyModal';
import UsageStatsCard from '../../components/usage/UsageStatsCard';
import keyManagementService from '../../services/keyManagement';
import type { Provider, UsageStatsResponse } from '../../types';

export default function HomeScreen() {
    const { user } = useAuth();
    const router = useRouter();
    const { hasCompletedOnboarding } = useOnboarding();
    const [providers, setProviders] = useState<Provider[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<{ name: string; displayName: string } | null>(null);

    // Usage stats state
    const [usageStats, setUsageStats] = useState<UsageStatsResponse | null>(null);
    const [usageLoading, setUsageLoading] = useState(false);

    // Fetch provider status
    const fetchProviders = async (forceRefresh = false) => {
        if (!user?.id) return;

        try {
            setLoading(true);
            const providerStatus = await keyManagementService.getProviderStatus(user.id, forceRefresh);
            setProviders(providerStatus.providers);
        } catch (error) {
            console.error('Error fetching providers:', error);
            Alert.alert('Error', 'Failed to load provider status');
        } finally {
            setLoading(false);
        }
    };

    const loadUsageStats = async () => {
        if (!user?.id) return;

        try {
            setUsageLoading(true);
            const stats = await keyManagementService.getUsageStats(user.id);
            setUsageStats(stats);
        } catch (error) {
            console.error('Error loading usage stats:', error);
            // Don't show alert for usage stats - fail silently
        } finally {
            setUsageLoading(false);
        }
    };

    const onRefresh = async () => {
        setRefreshing(true);
        await Promise.all([
            fetchProviders(true),
            loadUsageStats()
        ]);
        setRefreshing(false);
    };

    useEffect(() => {
        if (user?.id) {
            fetchProviders();
            loadUsageStats();
        }
    }, [user?.id]);

    const handleAddKey = (providerName: string) => {
        const provider = providers.find(p => p.name === providerName);
        if (provider) {
            setSelectedProvider({ name: provider.name, displayName: provider.displayName });
            setModalVisible(true);
        }
    };

    const handleSubmitKey = async (providerName: string, apiKey: string, apiSecret?: string) => {
        if (!user?.id) return;

        const result = await keyManagementService.addKey(user.id, providerName, apiKey, apiSecret);

        if (result.success) {
            Alert.alert('Success', result.message || 'API key added successfully');
            await loadProviderStatus(); // Refresh provider list
        } else {
            throw new Error(result.error || 'Failed to add API key');
        }
    };

    const handleTestKey = async (providerName: string) => {
        if (!user?.id) return;

        const result = await keyManagementService.testKey(user.id, providerName);

        Alert.alert(
            result.success ? 'Success' : 'Error',
            result.success ? '✅ API key is valid and working!' : `❌ ${result.error || 'Key test failed'}`
        );
    };

    const handleRemoveKey = async (providerName: string) => {
        if (!user?.id) return;

        Alert.alert(
            'Remove API Key',
            'Are you sure you want to remove this API key?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Remove',
                    style: 'destructive',
                    onPress: async () => {
                        const result = await keyManagementService.removeKey(user.id, providerName);

                        if (result.success) {
                            Alert.alert('Success', result.message || 'API key removed');
                            await loadProviderStatus(); // Refresh provider list
                        } else {
                            Alert.alert('Error', result.error || 'Failed to remove API key');
                        }
                    }
                }
            ]
        );
    };

    return (
        <ScrollView
            className="flex-1 bg-gray-900 p-4"
            refreshControl={
                <RefreshControl
                    refreshing={refreshing}
                    onRefresh={handleRefresh}
                    tintColor="#3B82F6"
                    colors={['#3B82F6']}
                />
            }
        >
            <View className="mb-8 mt-4">
                <Text className="text-gray-400 text-lg">Welcome back,</Text>
                <Text className="text-3xl font-bold text-white">{user?.name || 'Trader'}</Text>
            </View>

            {/* Page Header */}
            <View className="bg-gray-900 p-6">
                <Text className="text-white text-3xl font-bold mb-2">Provider Keys</Text>
                <Text className="text-gray-400">
                    Manage your API keys for data providers
                </Text>
            </View>

            {/* Usage Statistics Card */}
            <UsageStatsCard
                stats={usageStats}
                loading={usageLoading}
                onRefresh={loadUsageStats}
            />

            {/* Provider Cards */}
            <View className="p-4">
                {loading ? (
                    <Text className="text-gray-400 text-center">Loading providers...</Text>
                ) : (
                    providers.map((provider) => (
                        <ProviderKeyCard
                            key={provider.name}
                            provider={provider}
                            onAdd={handleAddKey}
                            onTest={handleTestKey}
                            onRemove={handleRemoveKey}
                        />
                    ))
                )}
            </View>

            <Text className="text-xl font-bold text-white mb-4">Quick Actions</Text>
            <View className="flex-row flex-wrap gap-4 mb-6">
                <TouchableOpacity
                    className="w-[47%] bg-gray-800 p-4 rounded-xl"
                    onPress={() => router.push('/(tabs)/learn')}
                >
                    <Text className="text-white font-bold text-lg mb-2">Continue Learning</Text>
                    <Text className="text-gray-400">Pick up where you left off</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    className="w-[47%] bg-gray-800 p-4 rounded-xl"
                    onPress={() => router.push('/(tabs)/market')}
                >
                    <Text className="text-white font-bold text-lg mb-2">Check Markets</Text>
                    <Text className="text-gray-400">View live prices</Text>
                </TouchableOpacity>
            </View>

            {/* Add Key Modal */}
            {selectedProvider && (
                <AddKeyModal
                    visible={modalVisible}
                    providerName={selectedProvider.name}
                    providerDisplayName={selectedProvider.displayName}
                    onClose={() => {
                        setModalVisible(false);
                        setSelectedProvider(null);
                    }}
                    onSubmit={handleSubmitKey}
                />
            )}
        </ScrollView>
    );
}
