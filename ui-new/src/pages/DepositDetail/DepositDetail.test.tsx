import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DepositDetail } from './DepositDetail';
import { getDeposit } from '@/api/deposits';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/deposits', async () => {
  const actual = await vi.importActual<typeof import('@/api/deposits')>('@/api/deposits');
  return {
    ...actual,
    getDeposit: vi.fn(),
  };
});

vi.mock('@/api/balance', () => ({
  getBalances: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

const mockDeposit = {
  id: 42,
  actor_entity_id: 1,
  from_entity_id: 100,
  from_entity: { id: 100, name: 'Keepz Provider', active: true },
  to_entity_id: 1,
  to_entity: { id: 1, name: 'Alice', active: true },
  to_treasury_id: null,
  to_treasury: null,
  amount: '25.00',
  currency: 'gel',
  status: 'pending',
  provider: 'keepz',
  details: {
    keepz: {
      payment_url: 'https://gateway.keepz.me/pay/abc123',
      payment_short_url: 'https://kz.example/abc123',
    },
  },
  created_at: '2026-03-09T00:00:00Z',
  modified_at: null,
};

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter initialEntries={['/deposits/42']}>
          <Routes>
            <Route path="/deposits/:id" element={ui} />
          </Routes>
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('DepositDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) =>
      selector({ actorEntity: { id: 1, name: 'Alice' } })
    );
    (getDeposit as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockDeposit);
    (getBalances as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(null);
  });

  it('renders the real payment flow without any dev-only completion controls', async () => {
    renderWithProviders(<DepositDetail />);

    const paymentLink = await screen.findByRole('link', { name: 'Continue payment' });
    expect(paymentLink).toHaveAttribute('href', 'https://gateway.keepz.me/pay/abc123');
    expect(screen.getByText('Pay from another device')).toBeInTheDocument();
    expect(screen.queryByText('Local dev')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Complete now' })).not.toBeInTheDocument();
    expect(screen.queryByText('Dev completion failed')).not.toBeInTheDocument();
  });
});
