import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Stack, TextInput } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { requestToken } from '@/api/auth';

const signInSchema = z.object({
  username: z.string().trim().min(1, 'Username is required'),
});

type SignInFormValues = z.infer<typeof signInSchema>;

export const SignInForm = () => {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loginLink, setLoginLink] = useState<string | null>(null);

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
      if (data.entity_found && data.token_generated) {
        if (data.message_sent) {
          setSuccessMessage('Success! Check your Telegram for the login link.');
          setLoginLink(null);
        } else if (data.login_link) {
          setSuccessMessage('Dev mode: Login link generated below.');
          try {
            const url = new URL(data.login_link);
            const path = url.pathname;
            setLoginLink(path);
          } catch {
            setLoginLink(null);
          }
        } else {
          setSuccessMessage('Token generated but message sending failed.');
          setLoginLink(null);
        }
      } else {
        setSuccessMessage(null);
        setLoginLink(null);
      }
    },
  });

  const onSubmit = (values: SignInFormValues) => {
    setSuccessMessage(null);
    setLoginLink(null);
    mutation.mutate(values.username);
  };

  return (
    <Stack gap="md">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <Stack gap="md">
          <TextInput
            label="Username"
            placeholder="Enter your username"
            error={errors.username?.message}
            {...register('username')}
          />
          <Button type="submit" loading={mutation.isPending} fullWidth>
            Request Login Link
          </Button>
        </Stack>
      </form>

      {mutation.isError && (
        <Alert color="gray" title="Error">
          {mutation.error.message}
        </Alert>
      )}

      {mutation.isSuccess && !mutation.data.entity_found && (
        <Alert color="gray" title="Authentication failed">
          Entity not found. Please check your username.
        </Alert>
      )}

      {successMessage && (
        <Alert color="gray" title="Success">
          {successMessage}
          {loginLink && (
            <div className="mt-2">
              <Button
                component="a"
                href={loginLink}
                variant="outline"
                color="gray"
                size="xs"
              >
                Log in directly (Dev)
              </Button>
            </div>
          )}
        </Alert>
      )}
    </Stack>
  );
};
