import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { TransactionDetailsModal } from './TransactionDetailsModal';
import type { Transaction } from '@/types/api';

const transaction: Transaction = {
  id: 801,
  created_at: '2026-02-18T11:00:00Z',
  from_entity_id: 3,
  from_entity: { id: 3, name: 'Alice', active: true, tags: [{ id: 1, name: 'member' }] },
  to_entity_id: 2,
  to_entity: { id: 2, name: 'Bob', active: true, tags: [{ id: 2, name: 'resident' }] },
  amount: '12.00',
  currency: 'usd',
  status: 'completed',
  tags: [{ id: 10, name: 'food' }],
  comment: 'This is the full transaction comment in the details modal.',
  invoice_id: 22,
  actor_entity_id: 1,
  actor_entity: { id: 1, name: 'Test User', active: true, tags: [{ id: 3, name: 'operator' }] },
  from_treasury_id: 5,
  to_treasury_id: 7,
  from_treasury: { id: 5, name: 'Cashbox' },
  to_treasury: { id: 7, name: 'Bank' },
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

describe('TransactionDetailsModal', () => {
  it('renders grouped details with author in the header meta area', () => {
    renderWithProviders(
      <TransactionDetailsModal opened={true} transaction={transaction} onClose={() => {}} />
    );

    expect(screen.getByText('Transaction #801')).toBeInTheDocument();
    expect(screen.getByText('12.00 USD')).toBeInTheDocument();
    expect(screen.getByText('Participants')).toBeInTheDocument();
    expect(screen.getByText('Context')).toBeInTheDocument();
    expect(screen.getByText('Comment')).toBeInTheDocument();
    expect(
      screen.getByText('This is the full transaction comment in the details modal.')
    ).toBeInTheDocument();
    expect(screen.getByText('Author')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open Test User profile' })).toHaveAttribute(
      'href',
      '/profile/1'
    );
    expect(screen.getByText('operator')).toBeInTheDocument();

    const participantsSection = screen.getByText('Participants').parentElement;
    if (!participantsSection) throw new Error('Participants section not found');

    expect(within(participantsSection).getByText('From')).toBeInTheDocument();
    expect(within(participantsSection).getByText('To')).toBeInTheDocument();
    expect(within(participantsSection).queryByText('Author')).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    renderWithProviders(
      <TransactionDetailsModal opened={true} transaction={transaction} onClose={onClose} />
    );

    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
