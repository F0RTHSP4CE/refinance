import { apiRequest } from './client';
import type { PaginatedResponse, Split } from '@/types/api';

export type GetSplitsParams = {
  actor_entity_id?: number;
  recipient_entity_id?: number;
  participant_entity_id?: number;
  performed?: boolean;
  currency?: string;
  amount_min?: number;
  amount_max?: number;
  comment?: string;
  tags_ids?: number[];
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getSplits = async (
  params: GetSplitsParams = {}
): Promise<PaginatedResponse<Split>> => {
  const searchParams = new URLSearchParams();
  if (params.actor_entity_id != null) {
    searchParams.set('actor_entity_id', String(params.actor_entity_id));
  }
  if (params.recipient_entity_id != null) {
    searchParams.set('recipient_entity_id', String(params.recipient_entity_id));
  }
  if (params.participant_entity_id != null) {
    searchParams.set('participant_entity_id', String(params.participant_entity_id));
  }
  if (params.performed != null) searchParams.set('performed', String(params.performed));
  if (params.currency) searchParams.set('currency', params.currency);
  if (params.amount_min != null) searchParams.set('amount_min', String(params.amount_min));
  if (params.amount_max != null) searchParams.set('amount_max', String(params.amount_max));
  if (params.comment) searchParams.set('comment', params.comment);
  params.tags_ids?.forEach((tagId) => searchParams.append('tags_ids', String(tagId)));
  if (params.skip != null) searchParams.set('skip', String(params.skip));
  if (params.limit != null) searchParams.set('limit', String(params.limit));

  const query = searchParams.toString();
  return apiRequest<PaginatedResponse<Split>>(query ? `splits?${query}` : 'splits', {
    signal: params.signal,
  });
};

export type SplitUpsertParams = {
  recipient_entity_id: number;
  amount: number;
  currency: string;
  comment?: string;
  tag_ids?: number[];
};

export const getSplit = async (id: number, signal?: AbortSignal): Promise<Split> => {
  return apiRequest<Split>(`splits/${id}`, { signal });
};

export const createSplit = async (params: SplitUpsertParams): Promise<Split> => {
  return apiRequest<Split>('splits', {
    method: 'POST',
    body: params,
  });
};

export const updateSplit = async (
  id: number,
  params: Partial<SplitUpsertParams>
): Promise<Split> => {
  return apiRequest<Split>(`splits/${id}`, {
    method: 'PATCH',
    body: params,
  });
};

export const deleteSplit = async (id: number): Promise<number> => {
  return apiRequest<number>(`splits/${id}`, {
    method: 'DELETE',
  });
};

export const performSplit = async (id: number): Promise<Split> => {
  return apiRequest<Split>(`splits/${id}/perform`, {
    method: 'POST',
  });
};

export type AddSplitParticipantParams =
  | {
      entity_id: number;
      fixed_amount?: number;
      entity_tag_id?: never;
    }
  | {
      entity_tag_id: number;
      fixed_amount?: number;
      entity_id?: never;
    };

export const addSplitParticipant = async (
  id: number,
  params: AddSplitParticipantParams
): Promise<Split> => {
  return apiRequest<Split>(`splits/${id}/participants`, {
    method: 'POST',
    body: params,
  });
};

export const removeSplitParticipant = async (id: number, entityId: number): Promise<Split> => {
  return apiRequest<Split>(`splits/${id}/participants?entity_id=${entityId}`, {
    method: 'DELETE',
  });
};
