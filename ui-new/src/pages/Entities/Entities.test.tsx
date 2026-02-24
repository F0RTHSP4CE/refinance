import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Entities } from './Entities';
import { createEntity, getEntities } from '@/api/entities';
import { getTags } from '@/api/tags';

vi.mock('@/api/entities', () => ({
  getEntities: vi.fn(),
  createEntity: vi.fn(),
}));

vi.mock('@/api/tags', () => ({
  getTags: vi.fn(),
  createTag: vi.fn(),
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
      <MantineProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('Entities page', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (getEntities as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 101,
          name: 'Resident Alice',
          active: true,
          comment: 'member',
          tags: [{ id: 2, name: 'resident' }],
          auth: null,
          created_at: '2026-01-10T10:00:00Z',
          modified_at: null,
        },
        {
          id: 102,
          name: 'Cash In',
          active: true,
          comment: 'system',
          tags: [{ id: 9, name: 'deposit' }],
          auth: null,
          created_at: '2026-01-10T10:00:00Z',
          modified_at: null,
        },
        {
          id: 103,
          name: 'Food Supplier',
          active: true,
          comment: 'vendor',
          tags: [{ id: 19, name: 'food' }],
          auth: null,
          created_at: '2026-01-10T10:00:00Z',
          modified_at: null,
        },
      ],
      total: 3,
      skip: 0,
      limit: 500,
    });

    (getTags as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        { id: 2, name: 'resident' },
        { id: 9, name: 'deposit' },
        { id: 19, name: 'food' },
      ],
      total: 3,
      skip: 0,
      limit: 500,
    });

    (createEntity as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 104,
      name: 'Utility Provider',
      active: true,
      comment: null,
      tags: [{ id: 7, name: 'utilities' }],
      auth: null,
      created_at: '2026-01-10T10:00:00Z',
      modified_at: null,
    });
  });

  it('shows only non-user entities', async () => {
    renderWithProviders(<Entities />);

    expect(await screen.findByText('Cash In')).toBeInTheDocument();
    expect(screen.getByText('Food Supplier')).toBeInTheDocument();
    expect(screen.queryByText('Resident Alice')).not.toBeInTheDocument();
  });

  it('renders entity name as profile link', async () => {
    renderWithProviders(<Entities />);

    const profileLink = await screen.findByRole('link', { name: 'Cash In' });
    expect(profileLink).toHaveAttribute('href', '/profile/102');
  });

  it('filters entities by selected tag', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Entities />);

    expect(await screen.findByText('Cash In')).toBeInTheDocument();
    expect(screen.getByText('Food Supplier')).toBeInTheDocument();

    const tagsFilterInput = screen.getByRole('textbox', { name: 'Tags filter' });
    await user.click(tagsFilterInput);
    await user.keyboard('{ArrowDown}{Enter}');

    expect(screen.getByText('Cash In')).toBeInTheDocument();
    expect(screen.queryByText('Food Supplier')).not.toBeInTheDocument();
  });
});
