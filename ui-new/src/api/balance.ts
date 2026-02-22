import { apiRequest } from './client';

export type Balances = {
  draft: Record<string, string>;
  completed: Record<string, string>;
};

export const getBalances = async (entityId: number, signal?: AbortSignal): Promise<Balances> => {
  return apiRequest<Balances>(`balances/${entityId}`, { signal });
};
