import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TelegramAuthButton } from './TelegramAuthButton';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/auth', () => ({
  telegramLogin: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

const mockAuthStore = {
  setToken: vi.fn(),
  loadActor: vi.fn(),
};

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

describe('TelegramAuthButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) =>
      selector(mockAuthStore)
    );
  });

  it('explains the localhost restriction without promising a direct local login link', () => {
    renderWithProviders(
      <TelegramAuthButton mode="login" botUsername="refinance_bot" enabled />
    );

    expect(
      screen.getByText(
        /On localhost, request a Telegram-delivered sign-in link below or open F0RTHSP4CE through a public URL registered for this bot\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Use username recovery below to request a Telegram-delivered sign-in link/i
      )
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continue with Telegram' })).toBeDisabled();
  });
});
