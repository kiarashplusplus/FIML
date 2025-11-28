import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Alert, RefreshControl, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../hooks/useAuth';
import ProviderKeyCard from '../../components/keys/ProviderKeyCard';
import AddKeyModal from '../../components/keys/AddKeyModal';
import UsageStatsCard from '../../components/usage/UsageStatsCard';
import keyManagementService from '../../services/keyManagement';
import type { Provider, UsageStatsResponse } from '../../types';

export default function HomeScreen() {
    const { user } = useAuth();
    const router = useRouter();
    const [providers, setProviders] = useState<Provider[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<{ name: string; displayName: string } | null>(null);

    const [searchQuery, setSearchQuery] = useState('');
    const [showPremium, setShowPremium] = useState(false);

    // Usage stats state
    const [usageStats, setUsageStats] = useState<UsageStatsResponse | null>(null);
    const [usageLoading, setUsageLoading] = useState(false);

    // Filter providers based on search
    const filteredProviders = providers.filter(provider => {
        const matchesSearch = (
            provider.displayName.toLowerCase().includes(searchQuery.toLowerCase()) ||
            provider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (provider.description && provider.description.toLowerCase().includes(searchQuery.toLowerCase()))
        );

        return matchesSearch;
    });

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
            await fetchProviders(); // Refresh provider list
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
                            await fetchProviders(); // Refresh provider list
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
                    onRefresh={onRefresh}
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
                <Text className="text-gray-400 mb-4">
                    Manage your API keys for data providers
                </Text>

                {/* Search Bar */}
                <View className="bg-gray-800 rounded-xl p-3 mb-4 flex-row items-center">
                    <Text className="text-gray-400 mr-2">🔍</Text>
                    <TextInput
                        className="flex-1 text-white text-base"
                        placeholder="Search providers..."
                        placeholderTextColor="#9CA3AF"
                        value={searchQuery}
                        onChangeText={setSearchQuery}
                    />
                    {searchQuery.length > 0 && (
                        <TouchableOpacity onPress={() => setSearchQuery('')}>
                            <Text className="text-gray-400">✕</Text>
                        </TouchableOpacity>
                    )}
                </View>
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
                    <>
                        {/* Free Providers Section */}
                        <View className="mb-6">
                            <Text className="text-white text-xl font-bold mb-4">Free / Public Providers</Text>
                            {filteredProviders.filter(p => p.tier === 'free').length === 0 ? (
                                <Text className="text-gray-400 italic">No free providers match your search.</Text>
                            ) : (
                                filteredProviders
                                    .filter(p => p.tier === 'free')
                                    .map((provider) => (
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

                        {/* Premium Providers Section */}
                        <View className="mb-6">
                            <TouchableOpacity
                                onPress={() => setShowPremium(!showPremium)}
                                className="flex-row items-center justify-between bg-gray-800 p-4 rounded-xl mb-4"
                            >
                                <View>
                                    <Text className="text-white text-lg font-bold">Premium Providers</Text>
                                    <Text className="text-gray-400 text-sm">
                                        {filteredProviders.filter(p => p.tier !== 'free').length} available
                                    </Text>
                                </View>
                                <Text className="text-blue-400 font-bold">
                                    {showPremium ? 'Hide' : 'Show'}
                                </Text>
                            </TouchableOpacity>

                            {showPremium && (
                                <View>
                                    {filteredProviders.filter(p => p.tier !== 'free').length === 0 ? (
                                        <Text className="text-gray-400 italic">No premium providers match your search.</Text>
                                    ) : (
                                        filteredProviders
                                            .filter(p => p.tier !== 'free')
                                            .map((provider) => (
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
                            )}
                        </View>
                    </>
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
