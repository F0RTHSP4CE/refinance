import { apiRequest } from './client';
import type { Entity, PaginatedResponse } from '@/types/api';

export const getMe = async (signal?: AbortSignal): Promise<Entity> => {
  return apiRequest<Entity>('entities/me', { signal });
};

export const getEntity = async (id: number, signal?: AbortSignal): Promise<Entity> => {
  return apiRequest<Entity>(`entities/${id}`, { signal });
};

type GetEntitiesParams = {
  name?: string;
  active?: boolean;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getEntities = async (
  params: GetEntitiesParams = {}
): Promise<PaginatedResponse<Entity>> => {
  const searchParams = new URLSearchParams();
  if (params.name) searchParams.set('name', params.name);
  if (params.active != null) searchParams.set('active', String(params.active));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));

  return apiRequest<PaginatedResponse<Entity>>(`entities?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type CreateEntityParams = {
  name: string;
  comment?: string;
  tag_ids?: number[];
};

export const createEntity = async (data: CreateEntityParams): Promise<Entity> => {
  return apiRequest<Entity>('entities', {
    method: 'POST',
    body: data,
  });
};

export type UpdateEntityParams = {
  name?: string;
  comment?: string;
  active?: boolean;
  tag_ids?: number[];
  auth?: {
    telegram_id?: string | number | null;
    signal_id?: string | number | null;
  };
};

export const updateEntity = async (id: number, data: UpdateEntityParams): Promise<Entity> => {
  return apiRequest<Entity>(`entities/${id}`, {
    method: 'PATCH',
    body: data,
  });
};
