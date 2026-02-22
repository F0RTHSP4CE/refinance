import { apiRequest } from './client';
import type { PaginatedResponse, Transaction } from '@/types/api';

type GetTransactionsParams = {
  entity_id: number;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getTransactions = async (
  params: GetTransactionsParams
): Promise<PaginatedResponse<Transaction>> => {
  const searchParams = new URLSearchParams();
  searchParams.set('entity_id', String(params.entity_id));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  return apiRequest<PaginatedResponse<Transaction>>(`transactions?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type CreateTransactionParams = {
  from_entity_id: number;
  to_entity_id: number;
  amount: number;
  currency: string;
  comment?: string;
  status?: 'draft' | 'completed';
  tag_ids?: number[];
};

export const createTransaction = async (data: CreateTransactionParams): Promise<Transaction> => {
  return apiRequest<Transaction>('transactions', {
    method: 'POST',
    body: data,
  });
};

export const completeTransaction = async (id: number): Promise<Transaction> => {
  return apiRequest<Transaction>(`transactions/${id}`, {
    method: 'PATCH',
    body: { status: 'completed' },
  });
};

export const getTransaction = async (id: number, signal?: AbortSignal): Promise<Transaction> => {
  return apiRequest<Transaction>(`transactions/${id}`, { signal });
};
