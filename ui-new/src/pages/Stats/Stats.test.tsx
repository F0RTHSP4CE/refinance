import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Stats } from './Stats';
import type { StatsBucketSum } from '@/api/stats';

const apiMocks = vi.hoisted(() => ({
  getResidentFeeSum: vi.fn(),
  getTransactionsSum: vi.fn(),
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

vi.mock('echarts', () => ({
  init: chartMocks.init.mockImplementation(() => ({
    setOption: chartMocks.setOption,
    resize: chartMocks.resize,
    dispose: chartMocks.dispose,
  })),
}));

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
            <Route path="/stats" element={<Stats />} />
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

  it('switches both queries to week grain when Week is selected', async () => {
    const user = userEvent.setup();

    renderWithProviders('/stats?from=2026-01-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole('radio', { name: 'Week' }));

    await waitFor(() => {
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
    });
  });

  it('applies Last 6 months preset to both endpoint queries', async () => {
    const user = userEvent.setup();
    const now = new Date();
    const expectedTo = formatDateInput(now);
    const expectedFrom = formatDateInput(subtractMonths(now, 6));

    renderWithProviders('/stats?from=2026-02-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(apiMocks.getResidentFeeSum).toHaveBeenCalled();
    });

    await user.click(screen.getByRole('button', { name: 'Last 6 months' }));

    await waitFor(() => {
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
  });

  it('renders chart options with 3 bar series and 1 total usd line', async () => {
    renderWithProviders('/stats?from=2026-02-01&to=2026-02-22&grain=month&preset=custom');

    await waitFor(() => {
      expect(chartMocks.setOption).toHaveBeenCalled();
    });

    const allOptions = chartMocks.setOption.mock.calls.map((call) => call[0] as { series?: unknown[] });
    expect(allOptions.some((option) => Array.isArray(option.series) && option.series.length === 4)).toBe(true);
  });

  it('shows empty states when both datasets are empty', async () => {
    apiMocks.getResidentFeeSum.mockResolvedValue([]);
    apiMocks.getTransactionsSum.mockResolvedValue([]);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('No resident fee data in the selected range.')).toBeInTheDocument();
      expect(screen.getByText('No transaction data in the selected range.')).toBeInTheDocument();
    });
  });
});
