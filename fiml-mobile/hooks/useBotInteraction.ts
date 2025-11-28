import { useState, useCallback } from 'react';
import { sendMessage as apiSendMessage, BotMessageResponse, BotMessageRequest } from '../services/api';

export interface Message {
    id: string;
    text: string;
    sender: 'user' | 'bot';
    timestamp: number;
    actions?: any[];
}

export const useBotInteraction = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const sendMessage = useCallback(async (text: string, userId: string) => {
        if (!text.trim()) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            text,
            sender: 'user',
            timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setIsLoading(true);
        setError(null);

        try {
            const response = await apiSendMessage({
                user_id: userId,
                platform: 'mobile_app',
                text,
            });

            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: response.text,
                sender: 'bot',
                timestamp: Date.now(),
                actions: response.actions,
            };

            setMessages((prev) => [...prev, botMsg]);
        } catch (err: any) {
            setError(err.message || 'Failed to send message');
            // Optional: remove user message on failure or show error state
        } finally {
            setIsLoading(false);
        }
    }, []);

    const sendAction = useCallback(async (action: string, userId: string, label: string) => {
        const isCommand = action.startsWith('/');

        // Optimistically add user message
        const userMsg: Message = {
            id: Date.now().toString(),
            text: label, // Show the label (e.g. "Start Lesson")
            sender: 'user',
            timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, userMsg]);
        setIsLoading(true);

        try {
            // If it's a command, send as text. If it's a callback, send as context action.
            const requestPayload: BotMessageRequest = isCommand
                ? { user_id: userId, platform: 'mobile_app', text: action }
                : { user_id: userId, platform: 'mobile_app', text: label, context: { action: action } };

            const response = await apiSendMessage(requestPayload);

            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: response.text,
                sender: 'bot',
                timestamp: Date.now(),
                actions: response.actions,
            };

            setMessages((prev) => [...prev, botMsg]);
        } catch (err: any) {
            setError(err.message || 'Failed to send action');
        } finally {
            setIsLoading(false);
        }
    }, []);

    return {
        messages,
        sendMessage,
        sendAction,
        isLoading,
        error,
    };
};
