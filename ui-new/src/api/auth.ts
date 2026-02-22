import { apiRequest } from './client';

export type TokenSendRequest = {
  entity_name: string;
};

export type TokenSendReport = {
  entity_found: boolean;
  token_generated: boolean;
  message_sent: boolean;
  login_link?: string | null;
};

export const requestToken = async (entityName: string): Promise<TokenSendReport> => {
  return apiRequest<TokenSendReport, TokenSendRequest>('tokens/send', {
    method: 'POST',
    body: { entity_name: entityName },
  });
};
