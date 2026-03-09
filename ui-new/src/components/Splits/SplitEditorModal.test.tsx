import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { SplitEditorModal } from './SplitEditorModal';
import { createSplit, updateSplit } from '@/api/splits';
import { getEntities } from '@/api/entities';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
}));

vi.mock('@/api/splits', () => ({
  createSplit: vi.fn(),
  updateSplit: vi.fn(),
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

describe('SplitEditorModal', () => {
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
    (createSplit as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 71,
      comment: 'March utilities',
    });
    (updateSplit as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 71,
      comment: 'March utilities',
    });
  });

  it('shows Name as the primary field and submits it through comment', async () => {
    const user = userEvent.setup();

    renderWithProviders(<SplitEditorModal opened={true} onClose={() => {}} />);

    expect(await screen.findByLabelText('Name')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Name'), 'March utilities');
    await user.clear(screen.getByLabelText('Amount'));
    await user.type(screen.getByLabelText('Amount'), '50');
    await user.click(screen.getByRole('button', { name: 'Create split' }));

    await waitFor(() => {
      expect(createSplit).toHaveBeenCalledWith({
        recipient_entity_id: 1,
        amount: 50,
        currency: 'GEL',
        comment: 'March utilities',
      });
    });
  });
});
