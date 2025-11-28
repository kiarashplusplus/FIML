import React from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../hooks/useAuth';

export default function HomeScreen() {
    const { user } = useAuth();
    const router = useRouter();

    return (
        <ScrollView className="flex-1 bg-gray-900 p-4">
            <View className="mb-8 mt-4">
                <Text className="text-gray-400 text-lg">Welcome back,</Text>
                <Text className="text-3xl font-bold text-white">{user?.name || 'Trader'}</Text>
            </View>

            <View className="flex-row space-x-4 mb-8">
                <View className="flex-1 bg-blue-600/20 p-4 rounded-xl border border-blue-600/50">
                    <Text className="text-blue-400 font-bold mb-1">XP Points</Text>
                    <Text className="text-2xl text-white font-bold">{user?.xp || 0}</Text>
                </View>
                <View className="flex-1 bg-purple-600/20 p-4 rounded-xl border border-purple-600/50">
                    <Text className="text-purple-400 font-bold mb-1">Level</Text>
                    <Text className="text-2xl text-white font-bold">Novice</Text>
                </View>
            </View>

            <Text className="text-xl font-bold text-white mb-4">Quick Actions</Text>
            <View className="flex-row flex-wrap gap-4">
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
        </ScrollView>
    );
}
