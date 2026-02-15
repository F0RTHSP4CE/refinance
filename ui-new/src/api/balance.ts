import { useAuthStore } from '@/stores/auth';
import { apiRequest } from './client';

export type Balances = {
  draft: Record<string, string>;
  completed: Record<string, string>;
};

export const getBalances = async (entityId: number): Promise<Balances> => {
  const token = useAuthStore.getState().token;
  return apiRequest<Balances>(`balances/${entityId}`, {
    token,
  });
};
