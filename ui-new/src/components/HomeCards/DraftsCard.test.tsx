import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { DraftsCard } from './DraftsCard';
import { useAuthStore } from '@/stores/auth';
import * as transactionsApi from '@/api/transactions';

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/transactions', () => ({
  getTransactions: vi.fn(),
}));

const mockActorEntity = { id: 1, name: 'Test User' };

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
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

describe('DraftsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockActorEntity);
  });

  it('renders empty state when there are no drafts', async () => {
    (transactionsApi.getTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 10,
    });

    renderWithProviders(<DraftsCard />);

    await waitFor(() => {
      expect(screen.getByText('No draft transactions')).toBeInTheDocument();
    });
  });

  it('opens draft modal when clicking a draft row', async () => {
    const user = userEvent.setup();
    (transactionsApi.getTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 501,
          created_at: '2026-02-18T11:00:00Z',
          from_entity_id: 3,
          from_entity: { id: 3, name: 'Alice', active: true, tags: [] },
          to_entity_id: 1,
          to_entity: { id: 1, name: 'Test User', active: true, tags: [] },
          amount: '20.00',
          currency: 'usd',
          status: 'draft',
          tags: [],
          actor_entity_id: 3,
          actor_entity: { id: 3, name: 'Alice', active: true, tags: [] },
          comment: 'Need approval',
          invoice_id: null,
          from_treasury_id: null,
          to_treasury_id: null,
          from_treasury: null,
          to_treasury: null,
        },
      ],
      total: 1,
      skip: 0,
      limit: 10,
    });

    renderWithProviders(<DraftsCard />);

    await waitFor(() => {
      expect(screen.getByText('Incoming request from Alice')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Incoming request from Alice'));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('heading', { name: 'Transaction #501' })).toBeInTheDocument();
    expect(within(dialog).getByText('Need approval')).toBeInTheDocument();
    expect(within(dialog).getByText('20.00 USD')).toBeInTheDocument();
  });
});
