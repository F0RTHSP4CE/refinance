import { create } from 'zustand';
import { ApiError, apiRequest } from '@/api/client';
import type { ActorEntity } from '@/types/api';

const TOKEN_KEY = 'refinance_token';

const setStoredToken = (token: string) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(TOKEN_KEY, token);
};

const clearStoredToken = () => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_KEY);
};

const getInitialToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
};

type AuthState = {
  token: string | null;
  actorEntity: ActorEntity | null;
  isLoading: boolean;
  isInitialized: boolean;
  authError: string | null;
  setToken: (token: string) => void;
  clearSession: () => void;
  loadActor: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getInitialToken(),
  actorEntity: null,
  isLoading: false,
  isInitialized: false,
  authError: null,
  setToken: (token: string) => {
    setStoredToken(token);
    set({ token, authError: null, isInitialized: false });
  },
  clearSession: () => {
    clearStoredToken();
    set({ token: null, actorEntity: null, authError: null, isLoading: false, isInitialized: true });
  },
  loadActor: async () => {
    const token = get().token;
    if (!token) {
      set({ actorEntity: null, authError: null, isLoading: false, isInitialized: true });
      return;
    }

    set({ isLoading: true, authError: null });
    try {
      const actorEntity = await apiRequest<ActorEntity>('entities/me', { token });
      setStoredToken(token);
      set({ actorEntity, isLoading: false, isInitialized: true });
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        clearStoredToken();
        set({
          token: null,
          actorEntity: null,
          isLoading: false,
          isInitialized: true,
          authError: null,
        });
        return;
      }

      const message = error instanceof ApiError ? error.message : 'Unknown authentication error';
      set({ actorEntity: null, isLoading: false, isInitialized: true, authError: message });
    }
  },
}));
