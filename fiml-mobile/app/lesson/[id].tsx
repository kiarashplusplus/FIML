import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, Stack } from 'expo-router';
import LessonViewer from '../../components/education/LessonViewer';

// Mock data - in real app this would come from API
const MOCK_LESSON_CONTENT = `
# Introduction to Technical Analysis

Technical analysis is a trading discipline employed to evaluate investments and identify trading opportunities by analyzing statistical trends gathered from trading activity, such as price movement and volume.

## Key Concepts

1. **Trend Lines**: Lines drawn on a chart to connect a series of prices.
2. **Support and Resistance**: Price levels where the stock has historically had difficulty falling below (support) or rising above (resistance).
3. **Moving Averages**: A calculation to analyze data points by creating a series of averages of different subsets of the full data set.

## Chart Patterns

- Head and Shoulders
- Double Top/Bottom
- Triangles
`;

export default function LessonScreen() {
    const { id } = useLocalSearchParams();

    // In a real app, fetch content based on ID
    // const { data, isLoading } = useLesson(id);

    return (
        <View className="flex-1 bg-gray-900">
            <Stack.Screen
                options={{
                    title: 'Lesson',
                    headerStyle: { backgroundColor: '#111827' },
                    headerTintColor: '#fff',
                }}
            />
            <LessonViewer content={MOCK_LESSON_CONTENT} />
        </View>
    );
}
