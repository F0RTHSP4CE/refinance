import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { Splits } from './Splits';
import { getEntities } from '@/api/entities';
import { getSplits } from '@/api/splits';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
}));

vi.mock('@/api/splits', () => ({
  getSplits: vi.fn(),
  getSplit: vi.fn(),
  createSplit: vi.fn(),
  updateSplit: vi.fn(),
  addSplitParticipant: vi.fn(),
  removeSplitParticipant: vi.fn(),
  performSplit: vi.fn(),
  deleteSplit: vi.fn(),
}));

vi.mock('@/api/tags', () => ({
  getTags: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
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
        <MemoryRouter initialEntries={['/splits']}>
          <Splits />
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('Splits page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      id: 1,
      name: 'Treasurer',
    });
    (getEntities as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        { id: 1, name: 'Treasurer' },
        { id: 2, name: 'Hackerspace' },
      ],
      total: 2,
      skip: 0,
      limit: 500,
    });
    (getSplits as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 71,
          created_at: '2026-03-01T12:00:00Z',
          modified_at: null,
          comment: 'March utilities',
          actor_entity: { id: 1, name: 'Treasurer', active: true, comment: '', tags: [] },
          recipient_entity: { id: 2, name: 'Hackerspace', active: true, comment: '', tags: [] },
          participants: [],
          amount: '50.00',
          currency: 'usd',
          collected_amount: '0.00',
          performed: false,
          share_preview: { current_share: '25.00', next_share: '25.00', average_share: '25.00' },
          performed_transactions: [],
          tags: [],
        },
      ],
      total: 1,
      skip: 0,
      limit: 20,
    });
  });

  it('renders visible summary and filters without legacy details blocks', async () => {
    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('How splits work')).toBeInTheDocument();
      expect(screen.getByText('Split filters')).toBeInTheDocument();
      expect(screen.getByText('March utilities')).toBeInTheDocument();
    });

    expect(document.querySelector('details')).toBeNull();
  });
});
