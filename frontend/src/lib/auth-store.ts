import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { StaffRead, StaffRole } from '@/types/api';
import { clearAuth, getAccessToken, getStoredUser, setAuth } from './api-client';

interface AuthState {
  user: StaffRead | null;
  token: string | null;
  isInitialized: boolean;
  setAuth: (token: string, user: StaffRead) => void;
  clearAuth: () => void;
  initialize: () => void;
  hasRole: (roles: StaffRole | StaffRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isInitialized: false,

      setAuth: (token: string, user: StaffRead) => {
        setAuth(token, user);
        set({ token, user, isInitialized: true });
      },

      clearAuth: () => {
        clearAuth();
        set({ token: null, user: null, isInitialized: true });
      },

      initialize: () => {
        if (get().isInitialized) return;
        const token = getAccessToken();
        const user = getStoredUser();
        set({ token, user, isInitialized: true });
      },

      hasRole: (roles) => {
        const user = get().user;
        if (!user) return false;
        const roleArray = Array.isArray(roles) ? roles : [roles];
        return roleArray.includes(user.role);
      },
    }),
    {
      name: 'raven-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist user, not token (token is in localStorage directly)
        user: state.user,
      }),
    }
  )
);
