import { useAuthStore } from '@/stores/auth';
import { apiRequest } from './client';
import type { Entity } from '@/types/api';

export const getMe = async (): Promise<Entity> => {
  const token = useAuthStore.getState().token;
  return apiRequest<Entity>('entities/me', { token });
};

export const getEntity = async (id: number): Promise<Entity> => {
  const token = useAuthStore.getState().token;
  return apiRequest<Entity>(`entities/${id}`, { token });
};
