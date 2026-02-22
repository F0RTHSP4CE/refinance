import { apiRequest } from './client';

export type EntityBalanceChangeByDay = {
  day: string;
  balance_changes: Record<string, number>;
  total_usd: number;
};

export type EntityMoneyFlowByDay = {
  day: string;
  incoming_total_usd: number;
  outgoing_total_usd: number;
};

export type TopEntityStat = {
  entity_id: number;
  entity_name: string;
  amounts: Record<string, number>;
  total_usd: number;
};

export type TopTagStat = {
  tag_id: number;
  tag_name: string;
  amounts: Record<string, number>;
  total_usd: number;
};

export type EntityStatsBundle = {
  cached: boolean;
  balance_changes: EntityBalanceChangeByDay[];
  transactions_by_day: { day: string; transaction_count: number }[];
  money_flow_by_day: EntityMoneyFlowByDay[];
  top_incoming: TopEntityStat[];
  top_outgoing: TopEntityStat[];
  top_incoming_tags: TopTagStat[];
  top_outgoing_tags: TopTagStat[];
};

export type EntityStatsParams = {
  months?: number;
  limit?: number;
  signal?: AbortSignal;
};

export const getEntityStatsBundle = async (
  entityId: number,
  params: EntityStatsParams = {}
): Promise<EntityStatsBundle> => {
  const search = new URLSearchParams();
  if (params.months != null) search.set('months', String(params.months));
  if (params.limit != null) search.set('limit', String(params.limit));
  const query = search.toString();
  const url = `stats/entity/${entityId}${query ? `?${query}` : ''}`;
  return apiRequest<EntityStatsBundle>(url, { signal: params.signal });
};
