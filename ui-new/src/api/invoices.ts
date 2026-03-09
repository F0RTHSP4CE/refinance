import { apiRequest } from './client';
import { createTransaction } from './transactions';
import type { Invoice, PaginatedResponse } from '@/types/api';
import type { Transaction } from '@/types/api';

export type GetInvoicesParams = {
  entity_id?: number;
  actor_entity_id?: number;
  from_entity_id?: number;
  to_entity_id?: number;
  status?: 'pending' | 'paid' | 'cancelled';
  billing_period?: string;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getInvoices = async (
  params: GetInvoicesParams
): Promise<PaginatedResponse<Invoice>> => {
  const searchParams = new URLSearchParams();
  if (params.entity_id != null) searchParams.set('entity_id', String(params.entity_id));
  if (params.actor_entity_id != null) {
    searchParams.set('actor_entity_id', String(params.actor_entity_id));
  }
  if (params.from_entity_id != null) {
    searchParams.set('from_entity_id', String(params.from_entity_id));
  }
  if (params.to_entity_id != null) searchParams.set('to_entity_id', String(params.to_entity_id));
  if (params.status) searchParams.set('status', params.status);
  if (params.billing_period) searchParams.set('billing_period', params.billing_period);
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return apiRequest<PaginatedResponse<Invoice>>(query ? `invoices?${query}` : 'invoices', {
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
  comment?: string;
  tag_ids?: number[];
};

export const createInvoice = async (params: CreateInvoiceParams): Promise<Invoice> => {
  return apiRequest<Invoice>('invoices', {
    method: 'POST',
    body: params,
  });
};

export type UpdateInvoiceParams = {
  amounts?: { currency: string; amount: number }[];
  billing_period?: string | null;
  comment?: string;
  tag_ids?: number[];
};

export const getInvoice = async (id: number, signal?: AbortSignal): Promise<Invoice> => {
  return apiRequest<Invoice>(`invoices/${id}`, { signal });
};

export const updateInvoice = async (id: number, params: UpdateInvoiceParams): Promise<Invoice> => {
  return apiRequest<Invoice>(`invoices/${id}`, {
    method: 'PATCH',
    body: params,
  });
};

export const deleteInvoice = async (id: number): Promise<number> => {
  return apiRequest<number>(`invoices/${id}`, {
    method: 'DELETE',
  });
};

export type PayInvoiceParams = {
  invoice: Invoice;
  currency: string;
  amount?: number;
};

export const payInvoice = async ({
  invoice,
  currency,
  amount,
}: PayInvoiceParams): Promise<Transaction> => {
  const selectedAmount = invoice.amounts.find(
    (entry) => entry.currency.toLowerCase() === currency.toLowerCase()
  );

  if (!selectedAmount && amount == null) {
    throw new Error('Selected invoice amount is not available for this currency.');
  }

  return createTransaction({
    from_entity_id: invoice.from_entity_id,
    to_entity_id: invoice.to_entity_id,
    amount: amount ?? Number(selectedAmount!.amount),
    currency,
    status: 'completed',
    invoice_id: invoice.id,
    comment: invoice.comment ?? undefined,
  });
};
