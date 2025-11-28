import { create } from 'zustand';

interface User {
    id: string;
    name: string;
    xp: number;
}

interface AppState {
    user: User | null;
    theme: 'light' | 'dark';
    activeSessionId: string | null;
    setUser: (user: User) => void;
    setTheme: (theme: 'light' | 'dark') => void;
    logout: () => void;
}

export const useStore = create<AppState>((set) => ({
    user: { id: 'demo-user', name: 'Demo User', xp: 0 }, // Default demo user
    theme: 'light',
    activeSessionId: null,
    setUser: (user) => set({ user }),
    setTheme: (theme) => set({ theme }),
    logout: () => set({ user: null, activeSessionId: null }),
}));
