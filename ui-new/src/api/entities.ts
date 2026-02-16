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
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getEntities = async (
  params: GetEntitiesParams = {}
): Promise<PaginatedResponse<Entity>> => {
  const searchParams = new URLSearchParams();
  if (params.name) searchParams.set('name', params.name);
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));

  return apiRequest<PaginatedResponse<Entity>>(`entities?${searchParams.toString()}`, {
    signal: params.signal,
  });
};
