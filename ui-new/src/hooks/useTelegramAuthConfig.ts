import { useQuery } from '@tanstack/react-query';
import { getTelegramAuthConfig } from '@/api/auth';

export const useTelegramAuthConfig = () => {
  return useQuery({
    queryKey: ['telegram-auth-config'],
    queryFn: ({ signal }) => getTelegramAuthConfig(signal),
    staleTime: 60_000,
  });
};
