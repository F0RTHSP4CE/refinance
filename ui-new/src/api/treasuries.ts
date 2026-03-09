import { apiRequest } from './client';
import type { BalanceSnapshot, EntityRef, PaginatedResponse } from '@/types/api';

export type Treasury = {
  id: number;
  name: string;
  comment?: string | null;
  active: boolean;
  author_entity_id: number | null;
  author_entity: EntityRef | null;
  balances: BalanceSnapshot | null;
  created_at: string;
  modified_at?: string | null;
};

type GetTreasuriesParams = {
  name?: string;
  active?: boolean;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getTreasuries = async (
  params: GetTreasuriesParams = {}
): Promise<PaginatedResponse<Treasury>> => {
  const searchParams = new URLSearchParams();
  if (params.name) searchParams.set('name', params.name);
  if (params.active != null) searchParams.set('active', String(params.active));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));

  return apiRequest<PaginatedResponse<Treasury>>(`treasuries?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type CreateTreasuryParams = {
  name: string;
  comment?: string;
  active?: boolean;
  author_entity_id?: number | null;
};

export const createTreasury = async (data: CreateTreasuryParams): Promise<Treasury> => {
  return apiRequest<Treasury>('treasuries', {
    method: 'POST',
    body: data,
  });
};

export type UpdateTreasuryParams = {
  name?: string;
  comment?: string;
  active?: boolean;
  author_entity_id?: number | null;
};

export const updateTreasury = async (id: number, data: UpdateTreasuryParams): Promise<Treasury> => {
  return apiRequest<Treasury>(`treasuries/${id}`, {
    method: 'PATCH',
    body: data,
  });
};
