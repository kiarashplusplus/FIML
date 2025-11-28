import { useState, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import { useRouter } from 'expo-router';
import { Platform } from 'react-native';

const ONBOARDING_KEY = 'has_completed_onboarding';

export const useOnboarding = () => {
    const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const router = useRouter();

    useEffect(() => {
        checkOnboardingStatus();
    }, []);

    const checkOnboardingStatus = async () => {
        try {
            let value: string | null = null;
            if (Platform.OS === 'web') {
                value = localStorage.getItem(ONBOARDING_KEY);
            } else {
                value = await SecureStore.getItemAsync(ONBOARDING_KEY);
            }
            setHasCompletedOnboarding(value === 'true');
        } catch (error) {
            console.error('Error checking onboarding status:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const completeOnboarding = async () => {
        try {
            if (Platform.OS === 'web') {
                localStorage.setItem(ONBOARDING_KEY, 'true');
            } else {
                await SecureStore.setItemAsync(ONBOARDING_KEY, 'true');
            }
            setHasCompletedOnboarding(true);
            router.replace('/(tabs)/chat');
        } catch (error) {
            console.error('Error completing onboarding:', error);
        }
    };

    const resetOnboarding = async () => {
        try {
            if (Platform.OS === 'web') {
                localStorage.removeItem(ONBOARDING_KEY);
            } else {
                await SecureStore.deleteItemAsync(ONBOARDING_KEY);
            }
            setHasCompletedOnboarding(false);
        } catch (error) {
            console.error('Error resetting onboarding:', error);
        }
    };

    return {
        hasCompletedOnboarding,
        isLoading,
        completeOnboarding,
        resetOnboarding,
        checkOnboardingStatus
    };
};
