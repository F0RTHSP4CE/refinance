import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { Transactions } from './Transactions';
import { useAuthStore } from '@/stores/auth';
import * as transactionsApi from '@/api/transactions';
import * as entitiesApi from '@/api/entities';
import * as tagsApi from '@/api/tags';

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/transactions', () => ({
  getAllTransactions: vi.fn(),
}));

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
}));

vi.mock('@/api/tags', () => ({
  getTags: vi.fn(),
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

describe('Transactions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockActorEntity);
    (entitiesApi.getEntities as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
    });
    (tagsApi.getTags as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
    });
  });

  it('renders shared transactions table with actor tags and truncated comments', async () => {
    (transactionsApi.getAllTransactions as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 801,
        created_at: '2026-02-18T11:00:00Z',
        from_entity_id: 3,
        from_entity: { id: 3, name: 'Alice', active: true, tags: [{ id: 1, name: 'member' }] },
        to_entity_id: 2,
        to_entity: { id: 2, name: 'Bob', active: true, tags: [{ id: 2, name: 'resident' }] },
        amount: '12.00',
        currency: 'usd',
        status: 'completed',
        tags: [],
        actor_entity_id: 1,
        actor_entity: {
          id: 1,
          name: 'Test User',
          active: true,
          tags: [{ id: 3, name: 'operator' }],
        },
        comment: 'This is a very long comment that should be truncated in table view.',
        invoice_id: null,
        from_treasury_id: null,
        to_treasury_id: null,
        from_treasury: null,
        to_treasury: null,
      },
    ]);

    renderWithProviders(<Transactions />);

    expect(await screen.findByText('Alice')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: 'Transactions' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('columnheader', { name: 'ID' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'From' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'To' })).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('This is a very long comment th...')).toBeInTheDocument();
    expect(
      screen.queryByText('This is a very long comment that should be truncated in table view.')
    ).not.toBeInTheDocument();

    const firstCallArg = (transactionsApi.getAllTransactions as ReturnType<typeof vi.fn>).mock
      .calls[0]?.[0];
    expect(firstCallArg).toBeDefined();
    expect(firstCallArg).not.toHaveProperty('entity_id');
  });

  it('opens transaction details modal on row click', async () => {
    const user = userEvent.setup();

    (transactionsApi.getAllTransactions as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 802,
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
        comment: 'snacks',
        invoice_id: null,
        from_treasury_id: null,
        to_treasury_id: null,
        from_treasury: null,
        to_treasury: null,
      },
    ]);

    renderWithProviders(<Transactions />);

    const row = await screen.findByText('802');
    const tableRow = row.closest('tr');
    if (!tableRow) throw new Error('Transaction row not found');

    await user.click(tableRow);

    const dialog = await screen.findByRole('dialog', { name: 'Transaction #802' });
    expect(within(dialog).getByRole('heading', { name: 'Transaction #802' })).toBeInTheDocument();
    expect(within(dialog).getByText('15.00 USD')).toBeInTheDocument();
  });

  it('keeps profile link navigation without opening modal', async () => {
    const user = userEvent.setup();

    (transactionsApi.getAllTransactions as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 803,
        created_at: '2026-02-18T11:00:00Z',
        from_entity_id: 3,
        from_entity: { id: 3, name: 'Alice', active: true, tags: [] },
        to_entity_id: 2,
        to_entity: { id: 2, name: 'Bob', active: true, tags: [] },
        amount: '20.00',
        currency: 'usd',
        status: 'completed',
        tags: [],
        actor_entity_id: 1,
        actor_entity: { id: 1, name: 'Test User', active: true, tags: [] },
        comment: 'snacks',
        invoice_id: null,
        from_treasury_id: null,
        to_treasury_id: null,
        from_treasury: null,
        to_treasury: null,
      },
    ]);

    renderWithProviders(<Transactions />);

    const aliceLink = await screen.findByRole('link', { name: 'Alice' });
    await user.click(aliceLink);

    expect(screen.queryByText('Transaction #803')).not.toBeInTheDocument();
  });

  it('renders empty state when there are no transactions', async () => {
    (transactionsApi.getAllTransactions as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    renderWithProviders(<Transactions />);

    await waitFor(() => {
      expect(screen.getByText('No matching transactions')).toBeInTheDocument();
    });
  });
});
