import React from 'react';
import { View } from 'react-native';
import ChatInterface from '../../components/chat/ChatInterface';

export default function ChatScreen() {
    return (
        <View className="flex-1 bg-gray-900">
            <ChatInterface />
        </View>
    );
}
