import { Alert, Box, Button, Stack, Text } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { IconBrandTelegram } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { telegramLogin, type TelegramAuthPayload } from '@/api/auth';
import { APP_BRAND } from '@/content/uiVocabulary';
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
    forthspaceTelegramAuth?: (user: TelegramWidgetUser) => void;
  }
}

// Legacy Telegram website-login widget used by the current hash-verification flow.
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
  const hostname = typeof window === 'undefined' ? '' : window.location.hostname;
  const isLocalOrigin = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]'].includes(hostname);
  const widgetEnabled = enabled && !isLocalOrigin;
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
      !widgetEnabled ||
      !normalizedBotUsername ||
      !containerRef.current ||
      widgetInitializedRef.current
    ) {
      return;
    }

    widgetInitializedRef.current = true;
    const container = containerRef.current;
    window.forthspaceTelegramAuth = (user) => {
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
    script.setAttribute('data-onauth', 'forthspaceTelegramAuth(user)');
    script.onerror = () => {
      setWidgetLoadError('Telegram widget could not be loaded in this environment.');
    };
    container.appendChild(script);

    return () => {
      if (container.contains(script)) {
        container.removeChild(script);
      }
      delete window.forthspaceTelegramAuth;
      widgetInitializedRef.current = false;
    };
  }, [mutation, normalizedBotUsername, widgetEnabled]);

  return (
    <Stack gap="sm">
      <Button
        component={widgetEnabled && fallbackUrl ? 'a' : 'button'}
        href={widgetEnabled ? (fallbackUrl ?? undefined) : undefined}
        target={widgetEnabled ? '_blank' : undefined}
        rel={widgetEnabled ? 'noreferrer' : undefined}
        fullWidth
        radius="xl"
        color="blue"
        disabled={!widgetEnabled || loading}
        loading={loading}
        leftSection={<IconBrandTelegram size={18} />}
      >
        {mode === 'connect' ? 'Connect via Telegram' : 'Continue with Telegram'}
      </Button>

      {widgetEnabled ? (
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
        {isLocalOrigin
          ? mode === 'connect'
            ? `Telegram linking needs the widget to run on a public URL registered for the ${APP_BRAND.shortName} bot.`
            : `On localhost, request a Telegram-delivered sign-in link below or open ${APP_BRAND.shortName} through a public URL registered for this bot.`
          : mode === 'connect'
            ? 'Authorize once in Telegram to link this account to your member profile.'
            : 'Use the Telegram widget above, or request a Telegram-delivered sign-in link below if the widget is blocked.'}
      </Text>

      {!enabled && !loading ? (
        <Alert color="gray" title="Telegram unavailable">
          {getUnavailableMessage(reason, mode)}
        </Alert>
      ) : null}

      {enabled && isLocalOrigin ? (
        <Alert color="yellow" title="Bot domain invalid on localhost">
          {mode === 'connect'
            ? 'Telegram rejects the website login widget on local origins. Open this app through a public HTTPS URL and register that URL for the bot in BotFather Web Login before linking Telegram.'
            : 'Telegram rejects the website login widget on local origins. Use username recovery below to request a Telegram-delivered sign-in link, or open this app through a public HTTPS URL and register that URL for the bot in BotFather Web Login.'}
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
