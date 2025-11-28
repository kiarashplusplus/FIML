import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';

interface Question {
    id: string;
    text: string;
    options: string[];
    correctIndex: number;
}

interface QuizInterfaceProps {
    title: string;
    questions: Question[];
    onComplete: (score: number) => void;
}

const QuizInterface: React.FC<QuizInterfaceProps> = ({ title, questions, onComplete }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [score, setScore] = useState(0);
    const [selectedOption, setSelectedOption] = useState<number | null>(null);
    const [isAnswered, setIsAnswered] = useState(false);

    const currentQuestion = questions[currentIndex];

    const handleOptionSelect = (index: number) => {
        if (isAnswered) return;
        setSelectedOption(index);
    };

    const handleSubmit = () => {
        if (selectedOption === null) return;

        const isCorrect = selectedOption === currentQuestion.correctIndex;
        if (isCorrect) {
            setScore(score + 1);
        }
        setIsAnswered(true);
    };

    const handleNext = () => {
        if (currentIndex < questions.length - 1) {
            setCurrentIndex(currentIndex + 1);
            setSelectedOption(null);
            setIsAnswered(false);
        } else {
            onComplete(score + (selectedOption === currentQuestion.correctIndex ? 1 : 0)); // Add last question score if correct
        }
    };

    return (
        <ScrollView className="flex-1 bg-gray-900 p-4">
            <Text className="text-2xl font-bold text-white mb-6">{title}</Text>

            <View className="mb-4">
                <Text className="text-gray-400 mb-2">Question {currentIndex + 1} of {questions.length}</Text>
                <View className="h-2 bg-gray-700 rounded-full">
                    <View
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
                    />
                </View>
            </View>

            <View className="bg-gray-800 p-6 rounded-xl mb-6">
                <Text className="text-xl text-white font-semibold mb-6">{currentQuestion.text}</Text>

                <View className="space-y-3">
                    {currentQuestion.options.map((option, index) => (
                        <TouchableOpacity
                            key={index}
                            onPress={() => handleOptionSelect(index)}
                            className={`p-4 rounded-lg border-2 ${isAnswered
                                    ? index === currentQuestion.correctIndex
                                        ? 'border-green-500 bg-green-500/10'
                                        : index === selectedOption
                                            ? 'border-red-500 bg-red-500/10'
                                            : 'border-gray-700'
                                    : selectedOption === index
                                        ? 'border-blue-500 bg-blue-500/10'
                                        : 'border-gray-700 bg-gray-700/50'
                                }`}
                        >
                            <Text className="text-white text-lg">{option}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            </View>

            <View className="flex-row justify-end">
                {!isAnswered ? (
                    <TouchableOpacity
                        onPress={handleSubmit}
                        disabled={selectedOption === null}
                        className={`px-6 py-3 rounded-lg ${selectedOption !== null ? 'bg-blue-600' : 'bg-gray-700'
                            }`}
                    >
                        <Text className="text-white font-bold text-lg">Submit Answer</Text>
                    </TouchableOpacity>
                ) : (
                    <TouchableOpacity
                        onPress={handleNext}
                        className="bg-blue-600 px-6 py-3 rounded-lg"
                    >
                        <Text className="text-white font-bold text-lg">
                            {currentIndex < questions.length - 1 ? 'Next Question' : 'Finish Quiz'}
                        </Text>
                    </TouchableOpacity>
                )}
            </View>
        </ScrollView>
    );
};

export default QuizInterface;
