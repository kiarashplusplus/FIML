import { View, SafeAreaView } from 'react-native';
import { ChatInterface } from '../../components/chat/ChatInterface';

export default function HomeScreen() {
    return (
        <SafeAreaView className="flex-1 bg-white">
            <ChatInterface />
        </SafeAreaView>
    );
}
