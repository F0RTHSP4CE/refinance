import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { SplitParticipantModal } from './SplitParticipantModal';
import { getEntities } from '@/api/entities';
import { addSplitParticipant, getSplit } from '@/api/splits';
import { getTags } from '@/api/tags';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
}));

vi.mock('@/api/splits', () => ({
  getSplit: vi.fn(),
  addSplitParticipant: vi.fn(),
}));

vi.mock('@/api/tags', () => ({
  getTags: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>{ui}</MantineProvider>
    </QueryClientProvider>
  );
};

describe('SplitParticipantModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      id: 1,
      name: 'Treasurer',
    });
    (getSplit as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 71,
      currency: 'usd',
      share_preview: { current_share: '10.00', next_share: '12.00', average_share: '11.00' },
    });
    (getEntities as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [{ id: 2, name: 'Resident Alice' }],
      total: 1,
      skip: 0,
      limit: 500,
    });
    (getTags as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [{ id: 3, name: 'resident' }],
      total: 1,
      skip: 0,
      limit: 500,
    });
    (addSplitParticipant as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 71 });
  });

  it('exposes a visible Entity/Tag mode switch in add mode', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <SplitParticipantModal opened={true} splitId={71} mode="add" onClose={() => {}} />
    );

    expect(await screen.findByText('Add by')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Entity' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Entity' })).toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'Tag' }));

    expect(screen.getByRole('textbox', { name: 'Entity tag' })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'Entity' })).not.toBeInTheDocument();
  });
});
