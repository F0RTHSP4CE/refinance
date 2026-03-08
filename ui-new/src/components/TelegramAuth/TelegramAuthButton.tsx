import { Alert, Box, Button, Stack, Text } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { IconBrandTelegram } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { telegramLogin, type TelegramAuthPayload } from '@/api/auth';
import { useAuthStore } from '@/stores/auth';

type TelegramWidgetUser = Omit<TelegramAuthPayload, 'link_to_current_entity'>;

type TelegramAuthButtonProps = {
  mode: 'login' | 'connect';
  botUsername?: string | null;
  enabled?: boolean;
  reason?: 'missing_bot_username' | 'missing_bot_token' | null;
  loading?: boolean;
  onSuccess?: () => void;
};

declare global {
  interface Window {
    refinanceTelegramAuth?: (user: TelegramWidgetUser) => void;
  }
}

const TELEGRAM_WIDGET_SRC = 'https://telegram.org/js/telegram-widget.js?22';

const getUnavailableMessage = (
  reason: TelegramAuthButtonProps['reason'],
  mode: TelegramAuthButtonProps['mode']
) => {
  if (reason === 'missing_bot_token') {
    return mode === 'connect'
      ? 'Telegram linking is configured in UI but disabled on the backend right now.'
      : 'Telegram sign-in is visible, but the backend bot token is not configured in this environment.';
  }

  return mode === 'connect'
    ? 'Telegram linking is not configured in this environment yet.'
    : 'Telegram sign-in is not configured in this environment yet.';
};

export const TelegramAuthButton = ({
  mode,
  botUsername,
  enabled = false,
  reason = null,
  loading = false,
  onSuccess,
}: TelegramAuthButtonProps) => {
  const normalizedBotUsername = botUsername?.trim() || null;
  const fallbackUrl = normalizedBotUsername ? `https://t.me/${normalizedBotUsername}` : null;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetInitializedRef = useRef(false);
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);
  const loadActor = useAuthStore((state) => state.loadActor);
  const [widgetLoadError, setWidgetLoadError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (user: TelegramWidgetUser) =>
      telegramLogin({
        ...user,
        link_to_current_entity: mode === 'connect',
      }),
    onSuccess: async (response) => {
      setToken(response.token);
      await loadActor();
      onSuccess?.();

      if (mode === 'login') {
        navigate('/', { replace: true });
      }
    },
  });

  useEffect(() => {
    if (
      !enabled ||
      !normalizedBotUsername ||
      !containerRef.current ||
      widgetInitializedRef.current
    ) {
      return;
    }

    widgetInitializedRef.current = true;
    const container = containerRef.current;
    window.refinanceTelegramAuth = (user) => {
      void mutation.mutate(user);
    };

    const script = document.createElement('script');
    script.async = true;
    script.src = TELEGRAM_WIDGET_SRC;
    script.setAttribute('data-telegram-login', normalizedBotUsername);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '999');
    script.setAttribute('data-userpic', 'false');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-onauth', 'refinanceTelegramAuth(user)');
    script.onerror = () => {
      setWidgetLoadError('Telegram widget could not be loaded in this environment.');
    };
    container.appendChild(script);

    return () => {
      if (container.contains(script)) {
        container.removeChild(script);
      }
      delete window.refinanceTelegramAuth;
      widgetInitializedRef.current = false;
    };
  }, [enabled, mutation, normalizedBotUsername]);

  return (
    <Stack gap="sm">
      <Button
        component={enabled && fallbackUrl ? 'a' : 'button'}
        href={enabled ? (fallbackUrl ?? undefined) : undefined}
        target={enabled ? '_blank' : undefined}
        rel={enabled ? 'noreferrer' : undefined}
        fullWidth
        radius="xl"
        color="blue"
        disabled={!enabled || loading}
        loading={loading}
        leftSection={<IconBrandTelegram size={18} />}
      >
        {mode === 'connect' ? 'Connect via Telegram' : 'Continue with Telegram'}
      </Button>

      {enabled ? (
        <Box
          ref={containerRef}
          style={{
            minHeight: 40,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        />
      ) : null}

      <Text size="sm" c="dimmed">
        {mode === 'connect'
          ? 'Authorize once in Telegram to link this account to your profile.'
          : 'Use the Telegram widget above, or open the bot manually if the widget is blocked.'}
      </Text>

      {!enabled && !loading ? (
        <Alert color="gray" title="Telegram unavailable">
          {getUnavailableMessage(reason, mode)}
        </Alert>
      ) : null}

      {widgetLoadError ? (
        <Alert color="blue" title="Widget unavailable">
          {widgetLoadError}
        </Alert>
      ) : null}

      {mutation.isError ? (
        <Alert
          color="red"
          title={
            mode === 'connect' ? 'Could not connect Telegram' : 'Could not sign in with Telegram'
          }
        >
          {mutation.error.message}
        </Alert>
      ) : null}
    </Stack>
  );
};
