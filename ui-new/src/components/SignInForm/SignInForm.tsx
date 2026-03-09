import { zodResolver } from '@hookform/resolvers/zod';
import { Accordion, Alert, Button, Divider, Stack, Text, TextInput } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { requestToken } from '@/api/auth';
import { TelegramAuthButton } from '@/components/TelegramAuth';
import { APP_BRAND } from '@/content/uiVocabulary';
import { useTelegramAuthConfig } from '@/hooks/useTelegramAuthConfig';

const signInSchema = z.object({
  username: z.string().trim().min(1, 'Username is required'),
});

type SignInFormValues = z.infer<typeof signInSchema>;

export const SignInForm = () => {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deliveryIssue, setDeliveryIssue] = useState<string | null>(null);
  const telegramConfigQuery = useTelegramAuthConfig();
  const telegramEnabled = telegramConfigQuery.data?.enabled ?? false;
  const usernameAccordionDefault = useMemo(
    () => (!telegramEnabled && !telegramConfigQuery.isLoading ? 'username' : null),
    [telegramConfigQuery.isLoading, telegramEnabled]
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInFormValues>({
    resolver: zodResolver(signInSchema),
  });

  const mutation = useMutation({
    mutationFn: (username: string) => requestToken(username),
    onSuccess: (data) => {
      setSuccessMessage(null);
      setDeliveryIssue(null);

      if (data.entity_found && data.token_generated) {
        if (data.message_sent) {
          setSuccessMessage('Check Telegram for your sign-in link.');
        } else {
          setDeliveryIssue(
            'The sign-in link was generated, but Telegram delivery failed. Make sure the bot can message this account and try again.'
          );
        }
      }
    },
  });

  const onSubmit = (values: SignInFormValues) => {
    setSuccessMessage(null);
    setDeliveryIssue(null);
    mutation.mutate(values.username);
  };

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <TelegramAuthButton
          mode="login"
          botUsername={telegramConfigQuery.data?.bot_username}
          enabled={telegramConfigQuery.data?.enabled}
          reason={telegramConfigQuery.data?.reason}
          loading={telegramConfigQuery.isLoading}
        />
        <Text size="sm" className="app-muted-copy">
          Telegram is the fastest route because it drops you back into {APP_BRAND.name} without the
          extra recovery step.
        </Text>
      </Stack>

      <Divider label="Recovery access" labelPosition="center" />

      <Accordion
        variant="separated"
        radius="lg"
        defaultValue={usernameAccordionDefault}
        styles={{
          item: {
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--app-border-subtle)',
          },
        }}
      >
        <Accordion.Item value="username">
          <Accordion.Control>
            <Stack gap={2}>
              <Text fw={700}>Use username recovery</Text>
              <Text size="sm" className="app-muted-copy">
                Request the Telegram-delivered sign-in link by username if the widget is blocked
                or you prefer opening the login from Telegram directly.
              </Text>
            </Stack>
          </Accordion.Control>
          <Accordion.Panel>
            <form onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
              <Stack gap="md">
                <TextInput
                  label="Username"
                  placeholder="Enter your username"
                  error={errors.username?.message}
                  {...register('username')}
                />
                <Button type="submit" loading={mutation.isPending} fullWidth>
                  Request Telegram sign-in link
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      {mutation.isError && (
        <Alert color="red" title="Could not request a login link">
          {mutation.error.message}
        </Alert>
      )}

      {mutation.isSuccess && !mutation.data.entity_found && (
        <Alert color="gray" title="Account not found">
          No matching member or actor was found for that username.
        </Alert>
      )}

      {successMessage && <Alert color="green" title="Login link ready">{successMessage}</Alert>}

      {deliveryIssue && (
        <Alert color="yellow" title="Telegram delivery failed">
          {deliveryIssue}
        </Alert>
      )}

      <Text size="sm" className="app-muted-copy">
        If Telegram says your account is not linked yet, connect Telegram from Profile after
        signing in through an existing session.
      </Text>
    </Stack>
  );
};
