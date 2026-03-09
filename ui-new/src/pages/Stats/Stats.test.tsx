import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { Stats } from './Stats';
import type { StatsBucketSum } from '@/api/stats';

const apiMocks = vi.hoisted(() => ({
  getResidentFeeSum: vi.fn(),
  getTransactionsSum: vi.fn(),
}));

const treasuryMocks = vi.hoisted(() => ({
  getTreasuries: vi.fn(),
}));

const currencyMocks = vi.hoisted(() => ({
  getExchangeRates: vi.fn(),
}));

const authMocks = vi.hoisted(() => ({
  useAuthStore: vi.fn(),
}));

const chartMocks = vi.hoisted(() => ({
  init: vi.fn(),
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock('@/api/stats', () => ({
  getResidentFeeSum: apiMocks.getResidentFeeSum,
  getTransactionsSum: apiMocks.getTransactionsSum,
}));

vi.mock('@/api/treasuries', () => ({
  getTreasuries: treasuryMocks.getTreasuries,
}));

vi.mock('@/api/currency-exchange', () => ({
  getExchangeRates: currencyMocks.getExchangeRates,
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: authMocks.useAuthStore,
}));

vi.mock('echarts', () => ({
  init: chartMocks.init.mockImplementation(() => ({
    setOption: chartMocks.setOption,
    resize: chartMocks.resize,
    dispose: chartMocks.dispose,
  })),
}));

const LocationDisplay = () => {
  const location = useLocation();
  return <output data-testid="location-search">{location.search}</output>;
};

const renderWithProviders = (initialEntry = '/stats') => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route
              path="/stats"
              element={
                <>
                  <Stats />
                  <LocationDisplay />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

const monthBuckets: StatsBucketSum[] = [
  {
    bucket_start: '2026-02-01',
    bucket_end: '2026-02-28',
    grain: 'month',
    amounts: { usd: 120, gel: 400, eur: 90 },
    total_usd: 315,
  },
];

const mockExchangeRates = [
  {
    currencies: [
      { code: 'USD', rate: '2.68', quantity: '1' },
      { code: 'EUR', rate: '2.9', quantity: '1' },
    ],
  },
];

const mockTreasuries = {
  items: [
    {
      id: 1,
      balances: {
        completed: {
          gel: '400.00',
          usd: '120.00',
          eur: '90.00',
        },
      },
    },
  ],
};

const pad = (value: number): string => String(value).padStart(2, '0');

const formatDateInput = (dt: Date): string =>
  `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`;

const subtractMonths = (dt: Date, months: number): Date => {
  const shifted = new Date(dt);
  const dayOfMonth = shifted.getDate();
  shifted.setDate(1);
  shifted.setMonth(shifted.getMonth() - months);
  const maxDay = new Date(shifted.getFullYear(), shifted.getMonth() + 1, 0).getDate();
  shifted.setDate(Math.min(dayOfMonth, maxDay));
  return shifted;
};

describe('Stats Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getResidentFeeSum.mockResolvedValue(monthBuckets);
    apiMocks.getTransactionsSum.mockResolvedValue(monthBuckets);
    treasuryMocks.getTreasuries.mockResolvedValue(mockTreasuries);
    currencyMocks.getExchangeRates.mockResolvedValue(mockExchangeRates);
    (authMocks.useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) =>
      selector({ actorEntity: { id: 1, name: 'F0' } })
    );
  });

  it('uses default last 3 months filters and month grain', async () => {
    const now = new Date();
    const expectedTo = formatDateInput(now);
    const expectedFrom = formatDateInput(subtractMonths(now, 3));

    renderWithProviders();

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalled();
      expect(apiMocks.getTransactionsSum).toHaveBeenCalled();
    });

    expect(apiMocks.getResidentFeeSum).toHaveBeenCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
    expect(apiMocks.getTransactionsSum).toHaveBeenCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
  });

  it('keeps grain changes local until Apply is clicked', async () => {
    const user = userEvent.setup();

    renderWithProviders('/stats?from=2026-01-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole('radio', { name: 'Week' }));

    expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
    expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    expect(screen.getByTestId('location-search')).toHaveTextContent('grain=month');

    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(2);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(2);
    });

    expect(apiMocks.getResidentFeeSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: '2026-01-01',
        timeframe_to: '2026-02-22',
        grain: 'week',
      })
    );
    expect(apiMocks.getTransactionsSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: '2026-01-01',
        timeframe_to: '2026-02-22',
        grain: 'week',
      })
    );
    expect(screen.getByTestId('location-search')).toHaveTextContent('grain=week');
  });

  it('applies Last 6 months preset only after Apply is clicked', async () => {
    const user = userEvent.setup();
    const now = new Date();
    const expectedTo = formatDateInput(now);
    const expectedFrom = formatDateInput(subtractMonths(now, 6));

    renderWithProviders('/stats?from=2026-02-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole('button', { name: 'Last 6 months' }));

    expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
    expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    expect(screen.getByTestId('location-search')).toHaveTextContent('from=2026-02-01');

    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(2);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(2);
    });

    expect(apiMocks.getResidentFeeSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
    expect(apiMocks.getTransactionsSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
  });

  it('prepares default filters on Reset without refetching until Apply', async () => {
    const user = userEvent.setup();
    const now = new Date();
    const expectedTo = formatDateInput(now);
    const expectedFrom = formatDateInput(subtractMonths(now, 3));

    renderWithProviders('/stats?from=2026-02-01&to=2026-02-22&grain=week&preset=custom');

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole('button', { name: 'Reset' }));

    expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
    expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('radio', { name: 'Month' })).toBeChecked();
    expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    expect(screen.getByTestId('location-search')).toHaveTextContent('grain=week');

    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(2);
      expect(apiMocks.getTransactionsSum).toHaveBeenCalledTimes(2);
    });

    expect(apiMocks.getResidentFeeSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
    expect(apiMocks.getTransactionsSum).toHaveBeenLastCalledWith(
      expect.objectContaining({
        timeframe_from: expectedFrom,
        timeframe_to: expectedTo,
        grain: 'month',
      })
    );
    expect(screen.getByTestId('location-search')).toHaveTextContent('grain=month');
  });

  it('renders chart options with 3 bar series and 1 total usd line', async () => {
    renderWithProviders('/stats?from=2026-02-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(chartMocks.setOption).toHaveBeenCalled();
    });

    const allOptions = chartMocks.setOption.mock.calls.map(
      (call) => call[0] as { series?: unknown[] }
    );
    expect(
      allOptions.some((option) => Array.isArray(option.series) && option.series.length === 4)
    ).toBe(true);
  });

  it('shows empty states when both datasets are empty', async () => {
    apiMocks.getResidentFeeSum.mockResolvedValue([]);
    apiMocks.getTransactionsSum.mockResolvedValue([]);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('No dues activity in the selected range.')).toBeInTheDocument();
      expect(screen.getByText('No transaction activity in the selected range.')).toBeInTheDocument();
    });
  });
});
