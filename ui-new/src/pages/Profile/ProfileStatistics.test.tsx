import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { ProfileStatistics } from './ProfileStatistics';

const apiMocks = vi.hoisted(() => ({
  getEntityStatsBundle: vi.fn(),
}));

const chartMocks = vi.hoisted(() => ({
  init: vi.fn(),
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock('@/api/stats', () => ({
  getEntityStatsBundle: apiMocks.getEntityStatsBundle,
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

const bundle = {
  cached: true,
  balance_changes: [
    { day: '2026-02-10', balance_changes: { usd: 10 }, total_usd: 10 },
    { day: '2026-02-20', balance_changes: { usd: 15 }, total_usd: 15 },
  ],
  transactions_by_day: [{ day: '2026-02-20', transaction_count: 2 }],
  money_flow_by_day: [
    { day: '2026-02-01', incoming_total_usd: 10, outgoing_total_usd: 2 },
    { day: '2026-02-10', incoming_total_usd: 20, outgoing_total_usd: 5 },
    { day: '2026-02-20', incoming_total_usd: 30, outgoing_total_usd: 10 },
  ],
  top_incoming: [],
  top_outgoing: [],
  top_incoming_tags: [],
  top_outgoing_tags: [],
};

const renderWithProviders = (initialEntry: string) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route
              path="/profile/:id"
              element={
                <>
                  <ProfileStatistics profileId={1} />
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

describe('ProfileStatistics filters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getEntityStatsBundle.mockResolvedValue(bundle);
  });

  it('keeps date changes local until Apply is clicked', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      '/profile/1?tab=statistics&from=2026-01-01&to=2026-02-22&grain=month&limit=8&preset=custom'
    );

    await screen.findByRole('button', { name: 'Apply' });
    expect(apiMocks.getEntityStatsBundle).toHaveBeenCalled();
    const initialCallCount = apiMocks.getEntityStatsBundle.mock.calls.length;

    const toInput = screen.getByLabelText('To');
    fireEvent.change(toInput, { target: { value: '2026-02-15' } });

    expect(apiMocks.getEntityStatsBundle.mock.calls.length).toBe(initialCallCount);

    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(apiMocks.getEntityStatsBundle.mock.calls.length).toBe(initialCallCount + 1);
    });

    expect(apiMocks.getEntityStatsBundle).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({
        timeframe_from: '2026-01-01',
        timeframe_to: '2026-02-15',
        limit: 8,
      })
    );
  });

  it('shows Reset only when draft differs from initial baseline', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      '/profile/1?tab=statistics&from=2026-01-01&to=2026-02-22&grain=month&limit=8&preset=custom'
    );

    await screen.findByRole('button', { name: 'Apply' });

    expect(screen.queryByRole('button', { name: 'Reset' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '12' }));

    expect(screen.getByRole('button', { name: 'Reset' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Reset' }));

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Reset' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });
  });

  it('keeps grain changes local until Apply updates the URL', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      '/profile/1?tab=statistics&from=2026-01-01&to=2026-02-22&grain=month&limit=8&preset=custom'
    );

    await screen.findByRole('button', { name: 'Apply' });
    const initialCallCount = apiMocks.getEntityStatsBundle.mock.calls.length;

    await user.click(screen.getByRole('radio', { name: 'Week' }));

    expect(apiMocks.getEntityStatsBundle.mock.calls.length).toBe(initialCallCount);
    expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    expect(screen.getByTestId('location-search')).toHaveTextContent('grain=month');

    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(screen.getByTestId('location-search')).toHaveTextContent('grain=week');
      expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });

    expect(apiMocks.getEntityStatsBundle.mock.calls.length).toBe(initialCallCount);
  });

  it('renders money flow chart with bars plus monthly overlay lines', async () => {
    renderWithProviders(
      '/profile/1?tab=statistics&from=2026-01-01&to=2026-02-22&grain=week&limit=8&preset=custom'
    );

    await screen.findByText('Income and spending');

    await waitFor(() => {
      expect(chartMocks.setOption).toHaveBeenCalled();
    });

    const moneyFlowOption = chartMocks.setOption.mock.calls
      .map(([option]) => option)
      .find((option) => {
        const maybeSeries = (option as { series?: Array<{ name?: string }> }).series;
        if (!maybeSeries || !Array.isArray(maybeSeries)) return false;
        return maybeSeries.some((series) => series.name === 'Income (USD)');
      }) as
      | {
          series: Array<{ name?: string; type?: string; data?: Array<number | null> }>;
        }
      | undefined;

    expect(moneyFlowOption).toBeDefined();
    if (!moneyFlowOption) {
      throw new Error('Money flow chart option was not captured');
    }

    const seriesNames = moneyFlowOption.series.map((series) => series.name);
    expect(seriesNames).toEqual(
      expect.arrayContaining([
        'Income (USD)',
        'Spending (USD)',
        'Monthly Income (USD)',
        'Monthly Spending (USD)',
      ])
    );

    const incomeBars = moneyFlowOption.series.find((series) => series.name === 'Income (USD)');
    const spendingBars = moneyFlowOption.series.find((series) => series.name === 'Spending (USD)');
    const monthlyIncome = moneyFlowOption.series.find(
      (series) => series.name === 'Monthly Income (USD)'
    );
    const monthlySpending = moneyFlowOption.series.find(
      (series) => series.name === 'Monthly Spending (USD)'
    );

    expect(incomeBars?.type).toBe('bar');
    expect(spendingBars?.type).toBe('bar');
    expect(monthlyIncome?.type).toBe('line');
    expect(monthlySpending?.type).toBe('line');

    expect(spendingBars?.data).toEqual(expect.arrayContaining([5, 10]));
    expect(spendingBars?.data).not.toEqual(expect.arrayContaining([-5, -10]));

    const monthlyIncomeData = monthlyIncome?.data ?? [];
    const monthlySpendingData = monthlySpending?.data ?? [];
    expect(monthlyIncomeData.some((value) => value === null)).toBe(true);
    expect(monthlySpendingData.some((value) => value === null)).toBe(true);
  });
});
