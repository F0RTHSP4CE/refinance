import { apiRequest } from './client';
import type { Invoice, PaginatedResponse } from '@/types/api';

type GetInvoicesParams = {
  entity_id: number;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getInvoices = async (
  params: GetInvoicesParams
): Promise<PaginatedResponse<Invoice>> => {
  const searchParams = new URLSearchParams();
  searchParams.set('entity_id', String(params.entity_id));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  return apiRequest<PaginatedResponse<Invoice>>(`invoices?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type GetPendingInvoicesParams = {
  from_entity_id: number;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getPendingInvoices = async (
  params: GetPendingInvoicesParams
): Promise<PaginatedResponse<Invoice>> => {
  const searchParams = new URLSearchParams();
  searchParams.set('from_entity_id', String(params.from_entity_id));
  searchParams.set('status', 'pending');
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  return apiRequest<PaginatedResponse<Invoice>>(`invoices?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type CreateInvoiceParams = {
  from_entity_id: number;
  to_entity_id: number;
  amounts: { currency: string; amount: number }[];
  billing_period?: string;
  tag_ids?: number[];
};

export const createInvoice = async (params: CreateInvoiceParams): Promise<Invoice> => {
  return apiRequest<Invoice>('invoices', {
    method: 'POST',
    body: JSON.stringify(params),
  });
};
