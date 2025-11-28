import React, { useState, useRef } from 'react';
import { View, TextInput, FlatList, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useMutation } from '@tanstack/react-query';
import { sendMessage, BotMessageRequest } from '../../services/api';
import { useStore } from '../../store';
import { MarkdownRenderer } from '../ui/MarkdownRenderer';

interface Message {
    id: string;
    text: string;
    sender: 'user' | 'bot';
    timestamp: number;
}

export const ChatInterface = () => {
    const [inputText, setInputText] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const user = useStore((state) => state.user);
    const flatListRef = useRef<FlatList>(null);

    const mutation = useMutation({
        mutationFn: (text: string) => {
            const request: BotMessageRequest = {
                user_id: user?.id || 'guest',
                platform: 'mobile_app',
                text: text,
            };
            return sendMessage(request);
        },
        onSuccess: (data) => {
            const botMessage: Message = {
                id: Date.now().toString(),
                text: data.text,
                sender: 'bot',
                timestamp: Date.now(),
            };
            setMessages((prev) => [botMessage, ...prev]);
        },
        onError: (error) => {
            console.error('Failed to send message', error);
            const errorMessage: Message = {
                id: Date.now().toString(),
                text: 'Sorry, I encountered an error. Please try again.',
                sender: 'bot',
                timestamp: Date.now(),
            };
            setMessages((prev) => [errorMessage, ...prev]);
        },
    });

    const handleSend = () => {
        if (!inputText.trim()) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            text: inputText,
            sender: 'user',
            timestamp: Date.now(),
        };

        setMessages((prev) => [userMessage, ...prev]);
        mutation.mutate(inputText);
        setInputText('');
    };

    const renderItem = ({ item }: { item: Message }) => (
        <View className={`my-2 p-3 rounded-lg max-w-[80%] ${item.sender === 'user' ? 'self-end bg-blue-500' : 'self-start bg-gray-200'}`}>
            {item.sender === 'user' ? (
                <Text className="text-white">{item.text}</Text>
            ) : (
                <MarkdownRenderer>{item.text}</MarkdownRenderer>
            )}
        </View>
    );

    return (
        <View className="flex-1 bg-white">
            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderItem}
                keyExtractor={(item) => item.id}
                inverted
                contentContainerStyle={{ padding: 16 }}
            />

            <View className="p-4 border-t border-gray-200 flex-row items-center">
                <TextInput
                    className="flex-1 bg-gray-100 p-3 rounded-full mr-2"
                    placeholder="Ask Maya about stocks..."
                    value={inputText}
                    onChangeText={setInputText}
                    onSubmitEditing={handleSend}
                />
                <TouchableOpacity
                    onPress={handleSend}
                    disabled={mutation.isPending}
                    className={`p-3 rounded-full ${mutation.isPending ? 'bg-gray-400' : 'bg-blue-600'}`}
                >
                    {mutation.isPending ? (
                        <ActivityIndicator color="white" size="small" />
                    ) : (
                        <Text className="text-white font-bold">Send</Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );
};
