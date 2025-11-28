import React, { useState } from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, Dimensions, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

const SLIDES = [
    {
        id: '1',
        title: 'AI-Native Finance',
        description: "Bloomberg's intelligence. API simplicity. $15/month. Give ChatGPT and Claude the same data quality as Wall Street.",
        icon: 'analytics-outline',
        color: '#3b82f6', // blue-500
    },
    {
        id: '2',
        title: 'Intelligent Arbitration',
        description: '5-Factor Provider Scoring across 17+ providers. We automatically route every query to the best source for freshness and accuracy.',
        icon: 'git-network-outline',
        color: '#8b5cf6', // violet-500
    },
    {
        id: '3',
        title: 'Enterprise Grade',
        description: 'Multilingual Compliance Guardrails in 9 languages. Built-in safety, rate limiting, and audit logging for production use.',
        icon: 'shield-checkmark-outline',
        color: '#f59e0b', // amber-500
    },
    {
        id: '4',
        title: 'Built for the Future',
        description: '10-Year Extensible Blueprint. Open Source. Explore our code and contribute to the future of financial intelligence.',
        icon: 'code-slash-outline',
        color: '#10b981', // emerald-500
        link: 'https://kiarashplusplus.github.io/FIML/',
        linkText: 'View Documentation',
    },
];

export default function OnboardingScreen() {
    const router = useRouter();
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

    const handleNext = () => {
        if (currentSlideIndex < SLIDES.length - 1) {
            setCurrentSlideIndex(currentSlideIndex + 1);
        } else {
            completeOnboarding();
        }
    };

    const handleSkip = () => {
        completeOnboarding();
    };

    const completeOnboarding = () => {
        router.replace('/(tabs)/home');
    };

    const handleLinkPress = async (url: string) => {
        const supported = await Linking.canOpenURL(url);
        if (supported) {
            await Linking.openURL(url);
        }
    };

    const Slide = ({ item }: { item: typeof SLIDES[0] }) => {
        return (
            <View className="flex-1 items-center justify-center px-8">
                <View
                    className="w-40 h-40 rounded-full items-center justify-center mb-10"
                    style={{ backgroundColor: `${item.color}20` }}
                >
                    <Ionicons name={item.icon as any} size={80} color={item.color} />
                </View>
                <Text className="text-3xl font-bold text-white text-center mb-4">
                    {item.title}
                </Text>
                <Text className="text-gray-400 text-lg text-center leading-6 mb-8">
                    {item.description}
                </Text>

                {item.link && (
                    <TouchableOpacity
                        onPress={() => handleLinkPress(item.link!)}
                        className="flex-row items-center bg-gray-800 px-4 py-2 rounded-lg border border-gray-700"
                    >
                        <Ionicons name="logo-github" size={20} color="white" style={{ marginRight: 8 }} />
                        <Text className="text-blue-400 font-semibold underline">
                            {item.linkText}
                        </Text>
                    </TouchableOpacity>
                )}
            </View>
        );
    };

    return (
        <SafeAreaView className="flex-1 bg-gray-900">
            <StatusBar style="light" />

            {/* Header with Skip button */}
            <View className="flex-row justify-end p-4">
                <TouchableOpacity onPress={handleSkip} className="px-4 py-2">
                    <Text className="text-gray-400 font-semibold text-base">Skip All</Text>
                </TouchableOpacity>
            </View>

            {/* Main Content */}
            <View className="flex-1">
                <Slide item={SLIDES[currentSlideIndex]} />
            </View>

            {/* Footer */}
            <View className="h-40 px-8 justify-between pb-8">
                {/* Pagination Dots */}
                <View className="flex-row justify-center space-x-2 mb-8">
                    {SLIDES.map((_, index) => (
                        <View
                            key={index}
                            className={`h-2 rounded-full transition-all duration-300 ${currentSlideIndex === index
                                ? 'w-8 bg-blue-500'
                                : 'w-2 bg-gray-700'
                                }`}
                        />
                    ))}
                </View>

                {/* Action Button */}
                <TouchableOpacity
                    onPress={handleNext}
                    className="bg-blue-600 py-4 rounded-xl items-center shadow-lg shadow-blue-900/20"
                    activeOpacity={0.8}
                >
                    <Text className="text-white font-bold text-lg">
                        {currentSlideIndex === SLIDES.length - 1 ? 'Get Started' : 'Next'}
                    </Text>
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
}
