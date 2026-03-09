import { apiRequest } from './client';
import type { PaginatedResponse, Transaction } from '@/types/api';

type GetTransactionsParams = {
  entity_id?: number;
  actor_entity_id?: number;
  from_entity_id?: number;
  to_entity_id?: number;
  invoice_id?: number;
  treasury_id?: number;
  amount_min?: number;
  amount_max?: number;
  currency?: string;
  comment?: string;
  status?: 'draft' | 'completed';
  from_treasury_id?: number;
  to_treasury_id?: number;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getTransactions = async (
  params: GetTransactionsParams
): Promise<PaginatedResponse<Transaction>> => {
  const searchParams = new URLSearchParams();
  if (params.entity_id != null) searchParams.set('entity_id', String(params.entity_id));
  if (params.actor_entity_id != null) {
    searchParams.set('actor_entity_id', String(params.actor_entity_id));
  }
  if (params.from_entity_id != null) {
    searchParams.set('from_entity_id', String(params.from_entity_id));
  }
  if (params.to_entity_id != null) searchParams.set('to_entity_id', String(params.to_entity_id));
  if (params.invoice_id != null) searchParams.set('invoice_id', String(params.invoice_id));
  if (params.treasury_id != null) searchParams.set('treasury_id', String(params.treasury_id));
  if (params.amount_min != null) searchParams.set('amount_min', String(params.amount_min));
  if (params.amount_max != null) searchParams.set('amount_max', String(params.amount_max));
  if (params.currency) searchParams.set('currency', params.currency);
  if (params.comment) searchParams.set('comment', params.comment);
  if (params.status) searchParams.set('status', params.status);
  if (params.from_treasury_id != null) {
    searchParams.set('from_treasury_id', String(params.from_treasury_id));
  }
  if (params.to_treasury_id != null) {
    searchParams.set('to_treasury_id', String(params.to_treasury_id));
  }
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
  invoice_id?: number | null;
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

export type UpdateTransactionParams = {
  amount?: number;
  currency?: string;
  comment?: string;
  status?: 'draft' | 'completed';
  invoice_id?: number | null;
  from_treasury_id?: number | null;
  to_treasury_id?: number | null;
  tag_ids?: number[];
};

export const updateTransaction = async (
  id: number,
  data: UpdateTransactionParams
): Promise<Transaction> => {
  return apiRequest<Transaction>(`transactions/${id}`, {
    method: 'PATCH',
    body: data,
  });
};

export const deleteTransaction = async (id: number): Promise<number> => {
  return apiRequest<number>(`transactions/${id}`, {
    method: 'DELETE',
  });
};
