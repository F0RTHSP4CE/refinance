import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { FeeInvoicesStatusCard } from './FeeInvoicesStatusCard';
import { useAuthStore } from '@/stores/auth';
import * as invoicesApi from '@/api/invoices';

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/invoices', () => ({
  getPendingInvoices: vi.fn(),
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

describe('FeeInvoicesStatusCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockActorEntity);
  });

  it('renders empty invoice state', async () => {
    (invoicesApi.getPendingInvoices as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 10,
    });

    renderWithProviders(<FeeInvoicesStatusCard />);

    await waitFor(() => {
      expect(screen.getByText('No unpaid dues')).toBeInTheDocument();
    });
  });

  it('renders pending invoice details and count badge', async () => {
    (invoicesApi.getPendingInvoices as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 101,
          created_at: '2026-02-18T10:00:00Z',
          billing_period: '2026-02-01',
          from_entity_id: 1,
          from_entity: { id: 1, name: 'Test User', active: true, tags: [] },
          to_entity_id: 2,
          to_entity: { id: 2, name: 'Hackerspace', active: true, tags: [] },
          amounts: [{ currency: 'usd', amount: '25.00' }],
          status: 'pending',
          tags: [],
          actor_entity_id: 1,
          actor_entity: { id: 1, name: 'Test User', active: true, tags: [] },
        },
      ],
      total: 1,
      skip: 0,
      limit: 10,
    });

    renderWithProviders(<FeeInvoicesStatusCard />);

    await waitFor(() => {
      expect(screen.getByText('Next to settle')).toBeInTheDocument();
      expect(screen.getByText('pending')).toBeInTheDocument();
      expect(screen.getByText('25.00 USD')).toBeInTheDocument();
    });
  });
});
