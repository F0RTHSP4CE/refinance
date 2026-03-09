import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { Fee } from './Fee';
import { getEntities } from '@/api/entities';
import { getFees } from '@/api/fees';
import { deleteInvoice, getInvoice, getInvoices } from '@/api/invoices';

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
}));

vi.mock('@/api/fees', () => ({
  getFees: vi.fn(),
}));

vi.mock('@/api/invoices', () => ({
  getInvoices: vi.fn(),
  getInvoice: vi.fn(),
  deleteInvoice: vi.fn(),
}));

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

const renderWithProviders = (initialEntry = '/fee?tab=fees') => {
  setDesktopMatchMedia();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Fee />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('Fee page', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (getEntities as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
    });

    (getInvoices as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
    });

    (getInvoice as ReturnType<typeof vi.fn>).mockResolvedValue(null);
    (deleteInvoice as ReturnType<typeof vi.fn>).mockResolvedValue(1);

    (getFees as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        entity: {
          id: 101,
          name: 'Resident Alice',
          active: true,
          comment: 'resident',
          tags: [],
          created_at: '2026-01-01T00:00:00Z',
        },
        fees: [
          {
            year: 2026,
            month: 1,
            amounts: { usd: '20.00' },
            total_usd: 20,
            paid_invoice_id: 41,
          },
          {
            year: 2026,
            month: 2,
            amounts: { usd: '21.50' },
            unpaid_invoice_amounts: { gel: '115.00', usd: '42.00' },
            total_usd: 21.5,
            unpaid_invoice_id: 42,
          },
          {
            year: 2026,
            month: 3,
            amounts: { gel: '18.00' },
            total_usd: 18,
          },
        ],
      },
    ]);
  });

  it(
    'shows reset range only after the filter changes and restores the initial state on reset',
    async () => {
    renderWithProviders();

    await screen.findByRole('region', { name: 'Resident fee matrix' });

    expect(screen.queryByRole('button', { name: 'Reset range' })).not.toBeInTheDocument();

    const [fromPeriodClearButton] = screen.getAllByRole('button', { name: '' });
    fireEvent.click(fromPeriodClearButton);

    expect(screen.getByRole('button', { name: 'Reset range' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Reset range' }));
    expect(screen.queryByRole('button', { name: 'Reset range' })).not.toBeInTheDocument();
    },
    10_000
  );

  it('renders the matrix in a horizontal scroll region with sticky columns and stacked amount lines', async () => {
    renderWithProviders();

    const region = await screen.findByRole('region', { name: 'Resident fee matrix' });
    expect(region).toHaveStyle({ overflowX: 'auto', overflowY: 'visible' });

    const residentHeader = screen.getByRole('columnheader', { name: 'Resident' });
    expect(residentHeader).toHaveStyle({ position: 'sticky', left: '0px', width: '240px' });

    const residentCell = screen.getByText('Resident Alice').closest('td');
    if (!residentCell) throw new Error('Resident cell not found');
    expect(residentCell).toHaveStyle({ position: 'sticky', left: '0px', width: '240px' });

    expect(screen.getByRole('link', { name: 'Resident Alice' })).toHaveAttribute(
      'href',
      '/profile/101'
    );

    const paidButton = screen.getByRole('button', {
      name: 'Open fee details for Resident Alice, January 2026, paid',
    });
    const pendingButton = screen.getByRole('button', {
      name: 'Open fee details for Resident Alice, February 2026, pending',
    });
    const emptyButton = screen.getByRole('button', {
      name: 'Open fee details for Resident Alice, March 2026, no invoice',
    });

    expect(paidButton).toHaveAttribute('data-fee-state', 'paid');
    expect(pendingButton).toHaveAttribute('data-fee-state', 'pending');
    expect(emptyButton).toHaveAttribute('data-fee-state', 'empty');

    expect(within(pendingButton).getByText('115.00 GEL')).toBeInTheDocument();
    expect(within(pendingButton).getByText('42.00 USD')).toBeInTheDocument();
  });

  it('opens the fee details modal when a fee tile is clicked', async () => {
    const user = userEvent.setup();

    renderWithProviders();

    const pendingButton = await screen.findByRole('button', {
      name: 'Open fee details for Resident Alice, February 2026, pending',
    });

    await user.click(pendingButton);

    expect(await screen.findByText('Pending invoice amounts')).toBeInTheDocument();
    expect(screen.getByText('115.00 GEL · 42.00 USD')).toBeInTheDocument();
  });
});
