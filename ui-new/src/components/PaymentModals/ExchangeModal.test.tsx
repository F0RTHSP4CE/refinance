import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { ExchangeModal } from './ExchangeModal';
import { useAuthStore } from '@/stores/auth';
import * as currencyExchangeApi from '@/api/currency-exchange';
import * as balanceApi from '@/api/balance';

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/currency-exchange', () => ({
  getExchangeRates: vi.fn(),
  previewExchange: vi.fn(),
  executeExchange: vi.fn(),
}));

vi.mock('@/api/balance', () => ({
  getBalances: vi.fn(),
}));

const mockRates = [
  {
    currencies: [
      { code: 'USD', rate: '2.68', quantity: '1' },
      { code: 'EUR', rate: '2.90', quantity: '1' },
    ],
  },
];

const mockBalances = {
  completed: {
    gel: '100.00',
    usd: '50.00',
    eur: '30.00',
  },
};

const mockActorEntity = { id: 1, name: 'Test User' };

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>{ui}</MantineProvider>
    </QueryClientProvider>
  );
};

describe('ExchangeModal', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      actorEntity: mockActorEntity,
    });
    (currencyExchangeApi.getExchangeRates as ReturnType<typeof vi.fn>).mockResolvedValue(mockRates);
    (balanceApi.getBalances as ReturnType<typeof vi.fn>).mockResolvedValue(mockBalances);
  });

  it('renders exchange modal with default currencies', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    expect(await screen.findByLabelText('From amount')).toBeInTheDocument();
    expect(screen.getByLabelText('To amount')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Review exchange' })).toBeDisabled();
  });

  it('shows exchange rate after loading', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/1 USD = /)).toBeInTheDocument();
    });
  });

  it('calculates target amount when source amount is entered', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const sourceInput = screen.getByLabelText('From amount');
    await user.type(sourceInput, '10');

    await waitFor(() => {
      const targetInput = screen.getByLabelText('To amount');
      expect(targetInput).toHaveValue('26.8');
    });
  });

  it('calculates source amount when target amount is entered', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const targetInput = screen.getByLabelText('To amount');
    await user.type(targetInput, '26.8');

    await waitFor(() => {
      const sourceInput = screen.getByLabelText('From amount');
      expect(sourceInput).toHaveValue('10');
    });
  });

  it('swaps currencies when swap button is clicked', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const sourceInput = screen.getByLabelText('From amount');
    await user.type(sourceInput, '10');

    await waitFor(() => {
      const targetInput = screen.getByLabelText('To amount');
      expect(targetInput).toHaveValue('26.8');
    });

    const swapButton = screen.getByRole('button', { name: 'Swap currencies' });
    await user.click(swapButton);

    await waitFor(() => {
      expect(screen.getByText(/1 GEL = /)).toBeInTheDocument();
    });
  });

  it('does not allow same currency selection', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const targetCurrencySelect = screen.getByRole('textbox', { name: 'To currency' });

    await user.click(targetCurrencySelect);
    await user.keyboard('{ArrowDown}{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/1 GEL = 0\.37 USD/)).toBeInTheDocument();
    });
  });

  it('disables exchange button when no amount is entered', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const exchangeButton = screen.getByRole('button', { name: 'Review exchange' });
    expect(exchangeButton).toBeDisabled();
  });

  it('enables exchange button when amount is entered', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const sourceInput = screen.getByLabelText('From amount');
    await user.type(sourceInput, '10');

    await waitFor(() => {
      const exchangeButton = screen.getByRole('button', { name: 'Review exchange' });
      expect(exchangeButton).not.toBeDisabled();
    });
  });

  it('shows preview step when exchange button is clicked', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const sourceInput = screen.getByLabelText('From amount');
    await user.type(sourceInput, '10');

    await waitFor(() => {
      const exchangeButton = screen.getByRole('button', { name: 'Review exchange' });
      expect(exchangeButton).not.toBeDisabled();
    });

    const exchangeButton = screen.getByRole('button', { name: 'Review exchange' });
    await user.click(exchangeButton);

    await waitFor(() => {
      expect(screen.getByText('Review exchange')).toBeInTheDocument();
      expect(screen.getByText('Exchange direction')).toBeInTheDocument();
    });
  });

  it('displays correct rate direction: USD to GEL should be ~2.68', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/1 USD = 2\.68 GEL/)).toBeInTheDocument();
    });
  });

  it('displays correct rate direction: GEL to USD should be ~0.37', async () => {
    renderWithProviders(<ExchangeModal opened={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });

    const swapButton = screen.getByRole('button', { name: 'Swap currencies' });
    await user.click(swapButton);

    await waitFor(() => {
      expect(screen.getByText(/1 GEL = 0\.37 USD/)).toBeInTheDocument();
    });
  });
});
