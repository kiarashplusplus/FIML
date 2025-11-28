import React from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

const LESSONS = [
    { id: '1', title: 'Introduction to Technical Analysis', duration: '10 min', level: 'Beginner' },
    { id: '2', title: 'Understanding Candlestick Patterns', duration: '15 min', level: 'Intermediate' },
    { id: '3', title: 'Risk Management Basics', duration: '12 min', level: 'Beginner' },
];

const QUIZZES = [
    { id: '1', title: 'Technical Analysis Basics', questions: 5 },
    { id: '2', title: 'Market Psychology', questions: 3 },
];

export default function LearnScreen() {
    const router = useRouter();

    return (
        <ScrollView className="flex-1 bg-gray-900 p-4">
            <Text className="text-3xl font-bold text-white mb-6 mt-4">Learn</Text>

            <Text className="text-xl font-bold text-white mb-4">Recommended Lessons</Text>
            <View className="space-y-4 mb-8">
                {LESSONS.map((lesson) => (
                    <TouchableOpacity
                        key={lesson.id}
                        className="bg-gray-800 p-4 rounded-xl border border-gray-700"
                        onPress={() => router.push(`/lesson/${lesson.id}`)}
                    >
                        <View className="flex-row justify-between items-start mb-2">
                            <Text className="text-white font-bold text-lg flex-1 mr-2">{lesson.title}</Text>
                            <View className="bg-blue-900/50 px-2 py-1 rounded">
                                <Text className="text-blue-400 text-xs">{lesson.level}</Text>
                            </View>
                        </View>
                        <Text className="text-gray-400">{lesson.duration}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <Text className="text-xl font-bold text-white mb-4">Quizzes</Text>
            <View className="space-y-4">
                {QUIZZES.map((quiz) => (
                    <TouchableOpacity
                        key={quiz.id}
                        className="bg-gray-800 p-4 rounded-xl border border-gray-700"
                        onPress={() => router.push(`/quiz/${quiz.id}`)}
                    >
                        <Text className="text-white font-bold text-lg mb-1">{quiz.title}</Text>
                        <Text className="text-gray-400">{quiz.questions} Questions</Text>
                    </TouchableOpacity>
                ))}
            </View>
        </ScrollView>
    );
}
