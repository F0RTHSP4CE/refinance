import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { Home } from './Home';

vi.mock('@/components/HomeCards', () => ({
  BalanceCard: () => <div data-testid="balance-card">Balance card</div>,
  FeeInvoicesStatusCard: () => <div data-testid="fee-card">Fee card</div>,
  DraftsCard: () => <div data-testid="drafts-card">Drafts card</div>,
  FridgeCoffeeCard: () => <div data-testid="supplies-card">Supplies card</div>,
  HomeTransactionsTableSection: () => <div data-testid="recent-movement-card">Recent movement</div>,
}));

vi.mock('@/components/ui', () => ({
  PageHeader: () => <div data-testid="page-header">Page header</div>,
}));

const renderWithProviders = () =>
  render(
    <MantineProvider>
      <Home />
    </MantineProvider>
  );

describe('Home', () => {
  it('renders balance first, secondary grid second, and recent movement last', () => {
    renderWithProviders();

    const balanceCard = screen.getByTestId('balance-card');
    const secondaryGrid = screen.getByTestId('home-secondary-grid');
    const recentMovement = screen.getByTestId('recent-movement-card');

    expect(balanceCard.compareDocumentPosition(secondaryGrid) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      secondaryGrid.compareDocumentPosition(recentMovement) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();

    const secondaryGridScope = within(secondaryGrid);
    expect(secondaryGridScope.getByTestId('fee-card')).toBeInTheDocument();
    expect(secondaryGridScope.getByTestId('drafts-card')).toBeInTheDocument();
    expect(secondaryGridScope.getByTestId('supplies-card')).toBeInTheDocument();
  });
});
