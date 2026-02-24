import { apiRequest } from './client';
import type { PaginatedResponse, Tag } from '@/types/api';

type GetTagsParams = {
  name?: string;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getTags = async (params: GetTagsParams = {}): Promise<PaginatedResponse<Tag>> => {
  const searchParams = new URLSearchParams();
  if (params.name) searchParams.set('name', params.name);
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));

  return apiRequest<PaginatedResponse<Tag>>(`tags?${searchParams.toString()}`, {
    signal: params.signal,
  });
};

export type CreateTagParams = {
  name: string;
  comment?: string;
};

export const createTag = async (data: CreateTagParams): Promise<Tag> => {
  return apiRequest<Tag>('tags', {
    method: 'POST',
    body: data,
  });
};
