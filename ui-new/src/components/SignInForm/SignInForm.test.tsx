import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SignInForm } from './SignInForm';
import { requestToken } from '@/api/auth';
import { useTelegramAuthConfig } from '@/hooks/useTelegramAuthConfig';

vi.mock('@/api/auth', () => ({
  requestToken: vi.fn(),
}));

vi.mock('@/hooks/useTelegramAuthConfig', () => ({
  useTelegramAuthConfig: vi.fn(),
}));

vi.mock('@/components/TelegramAuth', () => ({
  TelegramAuthButton: () => <div>Telegram widget</div>,
}));

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('SignInForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useTelegramAuthConfig as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        enabled: false,
        bot_username: null,
        reason: 'missing_bot_username',
      },
      isLoading: false,
    });
  });

  it('requests a Telegram-delivered sign-in link without rendering a local login button', async () => {
    const user = userEvent.setup();
    (requestToken as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      entity_found: true,
      token_generated: true,
      message_sent: true,
    });

    renderWithProviders(<SignInForm />);

    expect(
      screen.getByText(
        /Request the Telegram-delivered sign-in link by username if the widget is blocked/i
      )
    ).toBeInTheDocument();

    await user.type(screen.getByRole('textbox', { name: 'Username' }), 'alice');
    await user.click(screen.getByRole('button', { name: 'Request Telegram sign-in link' }));

    expect(await screen.findByText('Check Telegram for your sign-in link.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open generated link' })).not.toBeInTheDocument();
  });

  it('shows Telegram delivery troubleshooting when the login link cannot be sent', async () => {
    const user = userEvent.setup();
    (requestToken as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      entity_found: true,
      token_generated: true,
      message_sent: false,
    });

    renderWithProviders(<SignInForm />);

    await user.type(screen.getByRole('textbox', { name: 'Username' }), 'alice');
    await user.click(screen.getByRole('button', { name: 'Request Telegram sign-in link' }));

    expect(
      await screen.findByText(
        'The sign-in link was generated, but Telegram delivery failed. Make sure the bot can message this account and try again.'
      )
    ).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open generated link' })).not.toBeInTheDocument();
  });
});
