import { useAuthStore } from '@/stores/auth';
import { apiRequest } from './client';
import type { PaginatedResponse, Transaction } from '@/types/api';

type GetTransactionsParams = {
  entity_id: number;
  skip?: number;
  limit?: number;
};

export const getTransactions = async (
  params: GetTransactionsParams
): Promise<PaginatedResponse<Transaction>> => {
  const token = useAuthStore.getState().token;
  const searchParams = new URLSearchParams();
  searchParams.set('entity_id', String(params.entity_id));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  return apiRequest<PaginatedResponse<Transaction>>(
    `transactions?${searchParams.toString()}`,
    { token }
  );
};
