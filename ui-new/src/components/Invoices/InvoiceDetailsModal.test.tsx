import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { InvoiceDetailsModal } from './InvoiceDetailsModal';
import type { Invoice } from '@/types/api';

const invoice: Invoice = {
  id: 501,
  created_at: '2026-02-18T11:00:00Z',
  billing_period: '2026-02-01',
  from_entity_id: 3,
  from_entity: { id: 3, name: 'Resident Alice', active: true, tags: [{ id: 1, name: 'resident' }] },
  to_entity_id: 2,
  to_entity: { id: 2, name: 'Hackerspace', active: true, tags: [{ id: 2, name: 'house' }] },
  amounts: [
    { currency: 'usd', amount: '25.00' },
    { currency: 'gel', amount: '68.00' },
  ],
  comment: 'March utilities',
  status: 'pending',
  tags: [{ id: 10, name: 'utilities' }],
  actor_entity_id: 1,
  actor_entity: { id: 1, name: 'Treasurer', active: true, tags: [{ id: 3, name: 'operator' }] },
  transaction_id: null,
};

describe('InvoiceDetailsModal', () => {
  it('renders the shared section layout and pending actions', () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <InvoiceDetailsModal
            opened={true}
            invoice={invoice}
            onClose={() => {}}
            onEdit={() => {}}
            onPay={() => {}}
            onDelete={() => {}}
          />
        </MemoryRouter>
      </MantineProvider>
    );

    const dialog = screen.getByRole('dialog', { name: 'Invoice #501' });

    expect(within(dialog).getByRole('heading', { name: 'Invoice #501' })).toBeInTheDocument();
    expect(within(dialog).getByText('Amount')).toBeInTheDocument();
    expect(within(dialog).getByText('Participants')).toBeInTheDocument();
    expect(within(dialog).getByText('Context')).toBeInTheDocument();
    expect(within(dialog).getByText('Comment')).toBeInTheDocument();
    expect(within(dialog).getByText('Author: Treasurer')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: 'Open Resident Alice profile' })).toHaveAttribute(
      'href',
      '/profile/3'
    );
    expect(within(dialog).getByRole('link', { name: 'Open Hackerspace profile' })).toHaveAttribute(
      'href',
      '/profile/2'
    );
    expect(within(dialog).getByRole('button', { name: 'Pay' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('calls onClose from the persistent close action', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <MantineProvider>
        <MemoryRouter>
          <InvoiceDetailsModal opened={true} invoice={invoice} onClose={onClose} />
        </MemoryRouter>
      </MantineProvider>
    );

    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
