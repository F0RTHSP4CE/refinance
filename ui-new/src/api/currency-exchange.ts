import { apiRequest } from './client';

export type CurrencyExchangePreviewRequest = {
  entity_id: number;
  source_currency: string;
  source_amount?: number;
  target_currency: string;
  target_amount?: number;
  signal?: AbortSignal;
};

export type CurrencyExchangePreviewResponse = {
  entity_id: number;
  source_currency: string;
  source_amount: string;
  target_currency: string;
  target_amount: string;
  rate: string;
};

export type CurrencyExchangeRequest = {
  entity_id: number;
  source_currency: string;
  source_amount?: number;
  target_currency: string;
  target_amount?: number;
};

export type CurrencyExchangeReceipt = {
  source_currency: string;
  source_amount: string;
  target_currency: string;
  target_amount: string;
  rate: string;
  transactions: {
    id: number;
    comment: string;
    from_entity_id: number;
    to_entity_id: number;
    amount: number;
    currency: string;
    status: string;
  }[];
};

export type ExchangeRatesResponse = Record<string, unknown>;

export const previewExchange = async (params: CurrencyExchangePreviewRequest): Promise<CurrencyExchangePreviewResponse> => {
  const { signal, ...rest } = params;
  return apiRequest<CurrencyExchangePreviewResponse, Omit<CurrencyExchangePreviewRequest, 'signal'>>('/currency_exchange/preview', { method: 'POST', body: rest, signal });
};

export const executeExchange = async (params: CurrencyExchangeRequest): Promise<CurrencyExchangeReceipt> => {
  return apiRequest<CurrencyExchangeReceipt, CurrencyExchangeRequest>('/currency_exchange/exchange', { method: 'POST', body: params });
};

export const getExchangeRates = async (): Promise<ExchangeRatesResponse> => {
  return apiRequest<ExchangeRatesResponse>('/currency_exchange/rates', { method: 'GET' });
};
