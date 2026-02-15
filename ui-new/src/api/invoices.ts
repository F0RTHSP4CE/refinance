import { useAuthStore } from '@/stores/auth';
import { apiRequest } from './client';
import type { Invoice, PaginatedResponse } from '@/types/api';

type GetInvoicesParams = {
  entity_id: number;
  skip?: number;
  limit?: number;
};

export const getInvoices = async (
  params: GetInvoicesParams
): Promise<PaginatedResponse<Invoice>> => {
  const token = useAuthStore.getState().token;
  const searchParams = new URLSearchParams();
  searchParams.set('entity_id', String(params.entity_id));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  return apiRequest<PaginatedResponse<Invoice>>(
    `invoices?${searchParams.toString()}`,
    { token }
  );
};
