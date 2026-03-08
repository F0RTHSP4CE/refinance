import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { HomeTransactionsTableSection } from './HomeTransactionsTableSection';
import { useAuthStore } from '@/stores/auth';
import * as transactionsApi from '@/api/transactions';

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/transactions', () => ({
  getTransactions: vi.fn(),
}));

const mockActorEntity = { id: 1, name: 'Test User' };

const setDesktopMatchMedia = () => {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: query.includes('min-width'),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

const renderWithProviders = (ui: React.ReactElement) => {
  setDesktopMatchMedia();
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

describe('HomeTransactionsTableSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockActorEntity);
  });

  it('renders profile-style transactions table with data', async () => {
    (transactionsApi.getTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 701,
          created_at: '2026-02-18T11:00:00Z',
          from_entity_id: 3,
          from_entity: { id: 3, name: 'Alice', active: true, tags: [] },
          to_entity_id: 2,
          to_entity: { id: 2, name: 'Bob', active: true, tags: [] },
          amount: '15.00',
          currency: 'usd',
          status: 'completed',
          tags: [],
          actor_entity_id: 1,
          actor_entity: { id: 1, name: 'Test User', active: true, tags: [] },
          comment: 'Lunch',
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

    renderWithProviders(<HomeTransactionsTableSection />);

    await waitFor(() => {
      expect(screen.getByText(/Latest transactions/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'View all' })).toHaveAttribute(
        'href',
        '/transactions'
      );
      expect(screen.getByText('ID')).toBeInTheDocument();
      expect(screen.getByText('From')).toBeInTheDocument();
      expect(screen.getByText('To')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actor')).toBeInTheDocument();
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  it('renders empty table message when there are no transactions', async () => {
    (transactionsApi.getTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 10,
    });

    renderWithProviders(<HomeTransactionsTableSection />);

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'View all' })).toHaveAttribute(
        'href',
        '/transactions'
      );
      expect(screen.getByText('No transactions.')).toBeInTheDocument();
    });
  });

  it('opens transaction details modal when a row is clicked', async () => {
    const user = userEvent.setup();

    (transactionsApi.getTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 702,
          created_at: '2026-02-18T11:00:00Z',
          from_entity_id: 3,
          from_entity: { id: 3, name: 'Alice', active: true, tags: [] },
          to_entity_id: 2,
          to_entity: { id: 2, name: 'Bob', active: true, tags: [] },
          amount: '22.50',
          currency: 'usd',
          status: 'completed',
          tags: [],
          actor_entity_id: 1,
          actor_entity: { id: 1, name: 'Test User', active: true, tags: [] },
          comment: 'Lunch',
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

    renderWithProviders(<HomeTransactionsTableSection />);

    const row = await screen.findByText('702');
    const tableRow = row.closest('tr');
    if (!tableRow) throw new Error('Transaction row not found');

    await user.click(tableRow);

    const dialog = await screen.findByRole('dialog', { name: 'Transaction #702' });
    expect(within(dialog).getByText('22.50 USD')).toBeInTheDocument();
  });
});
