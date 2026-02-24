import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Users } from './Users';
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

describe('Users page', () => {
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
          name: 'Guest Bob',
          active: false,
          comment: 'guest',
          tags: [{ id: 15, name: 'guest' }],
          auth: null,
          created_at: '2026-01-10T10:00:00Z',
          modified_at: null,
        },
        {
          id: 103,
          name: 'Cash In',
          active: true,
          comment: 'system',
          tags: [{ id: 9, name: 'deposit' }],
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
        { id: 15, name: 'guest' },
        { id: 9, name: 'deposit' },
      ],
      total: 3,
      skip: 0,
      limit: 500,
    });

    (createEntity as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 104,
      name: 'Guest Bob',
      active: true,
      comment: null,
      tags: [{ id: 15, name: 'guest' }],
      auth: null,
      created_at: '2026-01-10T10:00:00Z',
      modified_at: null,
    });
  });

  it('shows only user-tagged entities', async () => {
    renderWithProviders(<Users />);

    expect(await screen.findByText('Resident Alice')).toBeInTheDocument();
    expect(screen.getByText('Guest Bob')).toBeInTheDocument();
    expect(screen.queryByText('Cash In')).not.toBeInTheDocument();
  });

  it('renders user name as profile link', async () => {
    renderWithProviders(<Users />);

    const profileLink = await screen.findByRole('link', { name: 'Resident Alice' });
    expect(profileLink).toHaveAttribute('href', '/profile/101');
  });

  it('filters users by selected tag', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Users />);

    expect(await screen.findByText('Resident Alice')).toBeInTheDocument();
    expect(screen.getByText('Guest Bob')).toBeInTheDocument();

    const tagsFilterInput = screen.getByRole('textbox', { name: 'Tags filter' });
    await user.click(tagsFilterInput);
    await user.keyboard('{ArrowDown}{Enter}');

    expect(screen.getByText('Resident Alice')).toBeInTheDocument();
    expect(screen.queryByText('Guest Bob')).not.toBeInTheDocument();
  });
});
