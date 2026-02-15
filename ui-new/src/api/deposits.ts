import { useAuthStore } from '@/stores/auth';
import { apiRequest } from './client';

export type EntityRef = {
  id: number;
  name: string;
  active: boolean;
};

export type TreasuryRef = {
  id: number;
  name: string;
  active: boolean;
};

export type Deposit = {
  id: number;
  actor_entity_id: number;
  from_entity_id: number;
  from_entity: EntityRef;
  to_entity_id: number;
  to_entity: EntityRef;
  to_treasury_id: number | null;
  to_treasury: TreasuryRef | null;
  amount: string;
  currency: string;
  status: string;
  provider: string;
  details: { keepz?: { payment_url?: string; payment_short_url?: string } } | null;
  created_at: string;
  modified_at: string | null;
};

export type KeepzDepositCreate = {
  to_entity_id: number;
  amount: number;
  currency: string;
};

export const createKeepzDeposit = async (
  params: KeepzDepositCreate
): Promise<Deposit> => {
  const token = useAuthStore.getState().token;
  const query = new URLSearchParams({
    to_entity_id: String(params.to_entity_id),
    amount: String(params.amount),
    currency: params.currency,
  });
  return apiRequest<Deposit>(`deposits/providers/keepz?${query}`, {
    method: 'POST',
    token,
  });
};

export const getDeposit = async (id: number): Promise<Deposit> => {
  const token = useAuthStore.getState().token;
  return apiRequest<Deposit>(`deposits/${id}`, { token });
};

export const getPaymentUrl = (deposit: Deposit): string | null => {
  const keepz = deposit.details?.keepz;
  return keepz?.payment_url ?? keepz?.payment_short_url ?? null;
};

const DEV_MODE_PAYMENT_URL = 'https://example.com/keepz-dev-payment-placeholder';

export const isDevModeDeposit = (deposit: Deposit): boolean => {
  const url = getPaymentUrl(deposit);
  return url === DEV_MODE_PAYMENT_URL;
};

export const completeDepositDev = async (depositId: number): Promise<Deposit> => {
  const token = useAuthStore.getState().token;
  return apiRequest<Deposit>(`deposits/${depositId}/complete-dev`, {
    method: 'POST',
    token,
  });
};
