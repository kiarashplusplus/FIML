import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import Markdown from 'react-native-markdown-display';

interface LessonViewerProps {
    content: string;
}

const LessonViewer: React.FC<LessonViewerProps> = ({ content }) => {
    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
            <Markdown
                style={{
                    body: { color: '#E5E7EB', fontSize: 16, lineHeight: 24 },
                    heading1: { color: '#FFFFFF', fontSize: 24, fontWeight: 'bold', marginBottom: 16 },
                    heading2: { color: '#FFFFFF', fontSize: 20, fontWeight: 'bold', marginTop: 16, marginBottom: 8 },
                    paragraph: { marginBottom: 12 },
                    code_inline: { backgroundColor: '#374151', color: '#E5E7EB', borderRadius: 4 },
                    code_block: { backgroundColor: '#1F2937', padding: 12, borderRadius: 8, marginVertical: 8 },
                }}
            >
                {content}
            </Markdown>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#111827', // gray-900
    },
    contentContainer: {
        padding: 16,
    },
});

export default LessonViewer;
