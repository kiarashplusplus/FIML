import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

export default function OnboardingScreen() {
    const router = useRouter();

    return (
        <View className="flex-1 justify-center items-center bg-gray-900 p-6">
            <Text className="text-4xl font-bold text-white mb-4 text-center">Welcome to FIML</Text>
            <Text className="text-xl text-gray-400 mb-12 text-center">
                Your AI-powered financial intelligence mentor. Learn, trade, and grow.
            </Text>

            <View className="w-full space-y-4">
                <TouchableOpacity
                    className="bg-blue-600 p-4 rounded-lg"
                    onPress={() => router.replace('/(auth)/login')}
                >
                    <Text className="text-white text-center font-bold text-lg">Get Started</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}
