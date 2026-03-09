import { apiRequest } from './client';

export type TokenSendRequest = {
  entity_name: string;
};

export type TokenSendReport = {
  entity_found: boolean;
  token_generated: boolean;
  message_sent: boolean;
};

export type TelegramAuthPayload = {
  id: number;
  first_name: string;
  auth_date: number;
  hash: string;
  username?: string;
  last_name?: string;
  photo_url?: string;
  link_to_current_entity?: boolean;
};

export type TelegramLoginResponse = {
  token: string;
  entity_id: number;
  linked: boolean;
};

export type TelegramAuthConfig = {
  enabled: boolean;
  bot_username: string | null;
  reason: 'missing_bot_username' | 'missing_bot_token' | null;
};

export const requestToken = async (entityName: string): Promise<TokenSendReport> => {
  return apiRequest<TokenSendReport, TokenSendRequest>('tokens/send', {
    method: 'POST',
    body: { entity_name: entityName },
  });
};

export const telegramLogin = async (
  payload: TelegramAuthPayload
): Promise<TelegramLoginResponse> => {
  return apiRequest<TelegramLoginResponse>('tokens/telegram-login', {
    method: 'POST',
    body: payload,
  });
};

export const getTelegramAuthConfig = async (signal?: AbortSignal): Promise<TelegramAuthConfig> => {
  return apiRequest<TelegramAuthConfig>('tokens/telegram-config', { signal });
};
