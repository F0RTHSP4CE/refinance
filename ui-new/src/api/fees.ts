import { apiRequest } from './client';
import type { FeeRow } from '@/types/api';

export type GetFeesParams = {
  months?: number;
  from_period?: string;
  to_period?: string;
  include_empty_entities?: boolean;
  include_empty_months?: boolean;
  signal?: AbortSignal;
};

export const getFees = async (params: GetFeesParams = {}): Promise<FeeRow[]> => {
  const searchParams = new URLSearchParams();
  if (params.months != null) searchParams.set('months', String(params.months));
  if (params.from_period) searchParams.set('from_period', params.from_period);
  if (params.to_period) searchParams.set('to_period', params.to_period);
  if (params.include_empty_entities != null) {
    searchParams.set('include_empty_entities', String(params.include_empty_entities));
  }
  if (params.include_empty_months != null) {
    searchParams.set('include_empty_months', String(params.include_empty_months));
  }
  const query = searchParams.toString();
  return apiRequest<FeeRow[]>(query ? `fees/?${query}` : 'fees/', {
    signal: params.signal,
  });
};
