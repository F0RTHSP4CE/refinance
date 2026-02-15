import { create } from 'zustand';
import { ApiError, apiRequest } from '@/api/client';
import type { ActorEntity } from '@/types/api';

const TOKEN_KEY = 'refinance_v2_token';

type AuthState = {
  token: string | null;
  actorEntity: ActorEntity | null;
  isLoading: boolean;
  authError: string | null;
  setToken: (token: string) => void;
  clearSession: () => void;
  loadActor: () => Promise<void>;
};

const getInitialToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(TOKEN_KEY);
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getInitialToken(),
  actorEntity: null,
  isLoading: false,
  authError: null,
  setToken: (token: string) => {
    window.localStorage.setItem(TOKEN_KEY, token);
    set({ token, authError: null });
  },
  clearSession: () => {
    window.localStorage.removeItem(TOKEN_KEY);
    set({ token: null, actorEntity: null, authError: null });
  },
  loadActor: async () => {
    const token = get().token;
    if (!token) {
      set({ actorEntity: null, authError: null });
      return;
    }

    set({ isLoading: true, authError: null });
    try {
      const actorEntity = await apiRequest<ActorEntity>('entities/me', { token });
      set({ actorEntity, isLoading: false });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Unknown authentication error';
      set({ actorEntity: null, isLoading: false, authError: message });
    }
  },
}));
