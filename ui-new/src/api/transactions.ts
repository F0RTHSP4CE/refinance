import { apiRequest } from './client';
import type { PaginatedResponse, Transaction } from '@/types/api';

type GetTransactionsParams = {
  entity_id?: number;
  status?: 'draft' | 'completed';
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getTransactions = async (
  params: GetTransactionsParams
): Promise<PaginatedResponse<Transaction>> => {
  const searchParams = new URLSearchParams();
  if (params.entity_id != null) searchParams.set('entity_id', String(params.entity_id));
  if (params.status) searchParams.set('status', params.status);
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  const endpoint = query ? `transactions?${query}` : 'transactions';
  return apiRequest<PaginatedResponse<Transaction>>(endpoint, {
    signal: params.signal,
  });
};

type GetAllTransactionsParams = {
  entity_id?: number;
  status?: 'draft' | 'completed';
  signal?: AbortSignal;
};

const TRANSACTIONS_PAGE_SIZE = 200;

export const getAllTransactions = async (
  params: GetAllTransactionsParams
): Promise<Transaction[]> => {
  const items: Transaction[] = [];
  let skip = 0;

  while (true) {
    const page = await getTransactions({
      entity_id: params.entity_id,
      status: params.status,
      skip,
      limit: TRANSACTIONS_PAGE_SIZE,
      signal: params.signal,
    });

    items.push(...page.items);
    skip += page.items.length;

    if (page.items.length === 0 || items.length >= page.total) {
      break;
    }
  }

  return items;
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
