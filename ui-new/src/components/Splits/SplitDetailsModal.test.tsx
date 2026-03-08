import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { SplitDetailsModal } from './SplitDetailsModal';
import { deleteSplit, getSplit, performSplit, removeSplitParticipant } from '@/api/splits';

vi.mock('@/api/splits', () => ({
  getSplit: vi.fn(),
  removeSplitParticipant: vi.fn(),
  performSplit: vi.fn(),
  deleteSplit: vi.fn(),
  getSplits: vi.fn(),
  updateSplit: vi.fn(),
  addSplitParticipant: vi.fn(),
}));

const renderWithProviders = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter>
          <SplitDetailsModal opened={true} splitId={71} onClose={() => {}} />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('SplitDetailsModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getSplit as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 71,
      created_at: '2026-03-01T12:00:00Z',
      modified_at: '2026-03-02T12:00:00Z',
      comment: 'March utilities',
      actor_entity: {
        id: 1,
        name: 'Treasurer',
        active: true,
        comment: '',
        tags: [{ id: 1, name: 'operator' }],
        created_at: '2026-01-01T00:00:00Z',
      },
      recipient_entity: {
        id: 2,
        name: 'Hackerspace',
        active: true,
        comment: '',
        tags: [{ id: 2, name: 'house' }],
        created_at: '2026-01-01T00:00:00Z',
      },
      participants: [
        {
          entity: {
            id: 3,
            name: 'Resident Alice',
            active: true,
            comment: '',
            tags: [{ id: 3, name: 'resident' }],
            created_at: '2026-01-01T00:00:00Z',
          },
          fixed_amount: '25.00',
        },
      ],
      amount: '25.00',
      currency: 'usd',
      collected_amount: '25.00',
      performed: true,
      share_preview: { current_share: '25.00', next_share: '25.00', average_share: '25.00' },
      performed_transactions: [
        {
          id: 900,
          created_at: '2026-03-03T12:00:00Z',
          from_entity_id: 3,
          from_entity: { id: 3, name: 'Resident Alice', active: true, tags: [] },
          to_entity_id: 2,
          to_entity: { id: 2, name: 'Hackerspace', active: true, tags: [] },
          amount: '25.00',
          currency: 'usd',
          status: 'completed',
          tags: [],
          comment: 'split payment',
          invoice_id: null,
          actor_entity_id: 1,
          actor_entity: { id: 1, name: 'Treasurer', active: true, tags: [] },
          from_treasury_id: null,
          to_treasury_id: null,
          from_treasury: null,
          to_treasury: null,
        },
      ],
      tags: [{ id: 10, name: 'utilities' }],
    });
    (removeSplitParticipant as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 71 });
    (performSplit as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 71 });
    (deleteSplit as ReturnType<typeof vi.fn>).mockResolvedValue(71);
  });

  it('renders the new section layout and still opens performed transactions', async () => {
    const user = userEvent.setup();

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('March utilities')).toBeInTheDocument();
      expect(screen.getByText('Amount')).toBeInTheDocument();
      expect(screen.getByText('Participants')).toBeInTheDocument();
      expect(screen.getByText('Context')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
      expect(screen.getByText('Performed transactions')).toBeInTheDocument();
    });

    const transactionRow = screen.getByText('#900').closest('tr');
    if (!transactionRow) throw new Error('Transaction row not found');

    await user.click(transactionRow);

    expect(await screen.findByRole('dialog', { name: 'Transaction #900' })).toBeInTheDocument();
  });
});
