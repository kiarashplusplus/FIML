import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../hooks/useAuth';

export default function LoginScreen() {
    const router = useRouter();
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleLogin = () => {
        if (username && password) {
            // Real login
            login({ username, password });
            router.replace('/(tabs)');
        } else {
            Alert.alert('Error', 'Please enter username and password');
        }
    };

    return (
        <View className="flex-1 justify-center items-center bg-gray-900 p-4">
            <Text className="text-3xl font-bold text-white mb-8">FIML Login</Text>

            <View className="w-full max-w-sm space-y-4">
                <View>
                    <Text className="text-gray-400 mb-2">Username</Text>
                    <TextInput
                        className="bg-gray-800 text-white p-4 rounded-lg border border-gray-700"
                        placeholder="Enter username"
                        placeholderTextColor="#6B7280"
                        value={username}
                        onChangeText={setUsername}
                        autoCapitalize="none"
                    />
                </View>

                <View>
                    <Text className="text-gray-400 mb-2">Password</Text>
                    <TextInput
                        className="bg-gray-800 text-white p-4 rounded-lg border border-gray-700"
                        placeholder="Enter password"
                        placeholderTextColor="#6B7280"
                        value={password}
                        onChangeText={setPassword}
                        secureTextEntry
                    />
                </View>

                <TouchableOpacity
                    className="bg-blue-600 p-4 rounded-lg mt-6"
                    onPress={handleLogin}
                >
                    <Text className="text-white text-center font-bold text-lg">Sign In</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    className="mt-4"
                    onPress={() => router.push('/(auth)/onboarding')}
                >
                    <Text className="text-blue-400 text-center">New user? Create an account</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}
