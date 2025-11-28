import React from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../hooks/useAuth';

export default function ProfileScreen() {
    const { user, logout } = useAuth();
    const router = useRouter();

    const handleLogout = () => {
        logout();
        router.replace('/(auth)/login');
    };

    return (
        <ScrollView className="flex-1 bg-gray-900 p-4">
            <View className="items-center mt-8 mb-8">
                <View className="w-24 h-24 bg-gray-700 rounded-full items-center justify-center mb-4">
                    <Text className="text-3xl text-white font-bold">
                        {user?.name?.charAt(0).toUpperCase() || 'U'}
                    </Text>
                </View>
                <Text className="text-2xl font-bold text-white">{user?.name}</Text>
                <Text className="text-gray-400">ID: {user?.id}</Text>
            </View>

            <View className="space-y-4">
                <View className="bg-gray-800 p-4 rounded-xl">
                    <Text className="text-gray-400 mb-1">Total XP</Text>
                    <Text className="text-2xl text-white font-bold">{user?.xp || 0}</Text>
                </View>

                <TouchableOpacity
                    className="bg-red-600/20 p-4 rounded-xl border border-red-600/50 mt-8"
                    onPress={handleLogout}
                >
                    <Text className="text-red-500 text-center font-bold text-lg">Log Out</Text>
                </TouchableOpacity>
            </View>
        </ScrollView>
    );
}
