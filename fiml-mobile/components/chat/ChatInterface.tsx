import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, KeyboardAvoidingView, Platform } from 'react-native';
import { useBotInteraction, Message } from '../../hooks/useBotInteraction';
import { useAuth } from '../../hooks/useAuth';

export default function ChatInterface() {
    const { user } = useAuth();
    const { messages, sendMessage, isLoading, error } = useBotInteraction();
    const [inputText, setInputText] = useState('');
    const flatListRef = useRef<FlatList>(null);

    const handleSend = () => {
        if (inputText.trim() && user) {
            sendMessage(inputText, user.id);
            setInputText('');
        }
    };

    useEffect(() => {
        if (messages.length > 0) {
            flatListRef.current?.scrollToEnd({ animated: true });
        }
    }, [messages]);

    const renderMessage = ({ item }: { item: Message }) => {
        const isUser = item.sender === 'user';
        return (
            <View className={`flex-row ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
                <View
                    className={`max-w-[80%] p-3 rounded-2xl ${isUser ? 'bg-blue-600 rounded-tr-none' : 'bg-gray-700 rounded-tl-none'
                        }`}
                >
                    <Text className="text-white text-base">{item.text}</Text>
                    <Text className="text-xs text-gray-400 mt-1">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Text>
                </View>
            </View>
        );
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            className="flex-1 bg-gray-900"
            keyboardVerticalOffset={100}
        >
            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={(item) => item.id}
                contentContainerStyle={{ padding: 16 }}
                className="flex-1"
                ListEmptyComponent={
                    <View className="flex-1 justify-center items-center mt-20">
                        <Text className="text-gray-500 text-lg">Start a conversation with your AI Mentor</Text>
                    </View>
                }
            />

            {error && (
                <View className="bg-red-500/20 p-2 mx-4 mb-2 rounded">
                    <Text className="text-red-400 text-center">{error}</Text>
                </View>
            )}

            <View className="p-4 bg-gray-800 border-t border-gray-700 flex-row items-center">
                <TextInput
                    className="flex-1 bg-gray-700 text-white p-3 rounded-xl mr-3 max-h-24"
                    placeholder="Ask about markets, crypto..."
                    placeholderTextColor="#9CA3AF"
                    value={inputText}
                    onChangeText={setInputText}
                    multiline
                />
                <TouchableOpacity
                    onPress={handleSend}
                    disabled={isLoading || !inputText.trim()}
                    className={`p-3 rounded-full ${isLoading || !inputText.trim() ? 'bg-gray-600' : 'bg-blue-600'
                        }`}
                >
                    <Text className="text-white font-bold">Send</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}
