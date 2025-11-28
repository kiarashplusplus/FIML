import React from 'react';
import { View, Alert } from 'react-native';
import { useLocalSearchParams, Stack, useRouter } from 'expo-router';
import QuizInterface from '../../components/education/QuizInterface';

const MOCK_QUESTIONS = [
    {
        id: 'q1',
        text: 'What is a "Bull Market"?',
        options: [
            'A market where prices are falling',
            'A market where prices are rising',
            'A market with no volatility',
            'A market for trading livestock'
        ],
        correctIndex: 1
    },
    {
        id: 'q2',
        text: 'Which of these is a momentum indicator?',
        options: [
            'RSI (Relative Strength Index)',
            'P/E Ratio',
            'Dividend Yield',
            'Market Cap'
        ],
        correctIndex: 0
    }
];

export default function QuizScreen() {
    const { id } = useLocalSearchParams();
    const router = useRouter();

    const handleComplete = (score: number) => {
        Alert.alert(
            'Quiz Completed!',
            `You scored ${score} out of ${MOCK_QUESTIONS.length}`,
            [
                { text: 'Back to Lessons', onPress: () => router.back() }
            ]
        );
    };

    return (
        <View className="flex-1 bg-gray-900">
            <Stack.Screen
                options={{
                    title: 'Quiz',
                    headerStyle: { backgroundColor: '#111827' },
                    headerTintColor: '#fff',
                }}
            />
            <QuizInterface
                title="Technical Analysis Basics"
                questions={MOCK_QUESTIONS}
                onComplete={handleComplete}
            />
        </View>
    );
}
