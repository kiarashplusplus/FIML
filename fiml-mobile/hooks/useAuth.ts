import { useStore } from '../store';
import { login as apiLogin } from '../services/api';

export const useAuth = () => {
    const { user, activeSessionId, setUser, logout } = useStore();

    const login = async (credentials: { username: string; password?: string }) => {
        try {
            // Call the API to login
            const response = await apiLogin(credentials);

            // In a real app, we'd store the token here
            // await SecureStore.setItemAsync('token', response.token);

            // Update store
            if (response.user) {
                setUser(response.user);
            }
            return true;
        } catch (error) {
            console.error('Login failed', error);
            return false;
        }
    };

    return {
        user,
        isAuthenticated: !!user,
        activeSessionId,
        login,
        logout,
    };
};
