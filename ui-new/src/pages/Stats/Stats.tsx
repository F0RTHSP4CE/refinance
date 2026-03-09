import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Group,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import * as echarts from 'echarts';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getExchangeRates, type ExchangeRateCurrency } from '@/api/currency-exchange';
import {
  getResidentFeeSum,
  getTransactionsSum,
  type StatsBucketSum,
  type StatsGrain,
} from '@/api/stats';
import { getTreasuries } from '@/api/treasuries';
import {
  AccentSurface,
  AppDateField,
  AppSegmentedControl,
  ChartCard,
  FilterBar,
  PageHeader,
  StatCard,
} from '@/components/ui';
import {
  CHART_AXIS_LABEL,
  CHART_AXIS_LINE,
  CHART_LEGEND_TEXT,
  CHART_SPLIT_LINE,
  CHART_TOOLTIP_BASE,
} from '@/constants/chartTheme';
import { APP_CHART_COLORS } from '@/constants/uiPalette';
import { useAuthStore } from '@/stores/auth';
import {
  DEFAULT_STATS_GRAIN,
  DEFAULT_STATS_PRESET,
  STATS_PRESET_OPTIONS,
  areStatsFiltersEqual,
  formatDateInput,
  getPresetRange,
  isStatsFilterPreset,
  isStatsGrain,
  normalizeRange,
  parseDateInput,
  type StatsFilterPreset,
  type StatsFiltersValue,
} from '@/components/ui/statsFilterUtils';

const DEFAULT_GRAIN = DEFAULT_STATS_GRAIN;
const DEFAULT_PRESET = DEFAULT_STATS_PRESET;
const FALLBACK_CURRENCIES = ['usd', 'gel', 'eur'];
const TRACKED_BALANCE_CURRENCIES = ['GEL', 'USD', 'EUR'] as const;

const CURRENCY_COLORS = [
  APP_CHART_COLORS.blue,
  APP_CHART_COLORS.lime,
  APP_CHART_COLORS.amber,
];
const TOTAL_USD_LINE_COLOR = APP_CHART_COLORS.coral;
const pad = (value: number): string => String(value).padStart(2, '0');

const getIsoWeek = (dt: Date): { year: number; week: number } => {
  const utcDate = new Date(Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate()));
  const day = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((utcDate.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: utcDate.getUTCFullYear(), week };
};

const formatBucketLabel = (bucketStart: string, grain: StatsGrain): string => {
  const dt = parseDateInput(bucketStart);
  if (!dt) return bucketStart;
  if (grain === 'month') {
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}`;
  }
  const isoWeek = getIsoWeek(dt);
  return `${isoWeek.year}-W${pad(isoWeek.week)}`;
};

const formatNumber = (value: number): string =>
  Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const getAmountForCurrency = (amounts: Record<string, number>, currency: string): number => {
  const normalized = currency.toLowerCase();
  for (const [key, value] of Object.entries(amounts)) {
    if (key.toLowerCase() === normalized) return Number(value) || 0;
  }
  return 0;
};

const getCurrencyUnitInGel = (currency: string, rates: ExchangeRateCurrency[]): number | null => {
  if (currency.toUpperCase() === 'GEL') return 1;
  const rate = rates.find((item) => item.code.toUpperCase() === currency.toUpperCase());
  if (!rate) return null;
  const rateValue = Number(rate.rate);
  const quantityValue = Number(rate.quantity);
  if (!Number.isFinite(rateValue) || !Number.isFinite(quantityValue) || quantityValue === 0) {
    return null;
  }
  return rateValue / quantityValue;
};

const convertCurrencyAmount = (
  amount: number,
  sourceCurrency: string,
  targetCurrency: string,
  rates: ExchangeRateCurrency[]
): number | null => {
  if (sourceCurrency.toUpperCase() === targetCurrency.toUpperCase()) {
    return amount;
  }

  const sourceUnitInGel = getCurrencyUnitInGel(sourceCurrency, rates);
  const targetUnitInGel = getCurrencyUnitInGel(targetCurrency, rates);

  if (sourceUnitInGel == null || targetUnitInGel == null) {
    return null;
  }

  return amount * (sourceUnitInGel / targetUnitInGel);
};

const pickTopCurrencies = (buckets: StatsBucketSum[]): string[] => {
  const totals = new Map<string, number>();

  for (const bucket of buckets) {
    for (const [rawCurrency, rawAmount] of Object.entries(bucket.amounts)) {
      const currency = rawCurrency.toLowerCase();
      const amount = Math.abs(Number(rawAmount) || 0);
      totals.set(currency, (totals.get(currency) ?? 0) + amount);
    }
  }

  const sorted = Array.from(totals.entries())
    .sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1];
      return a[0].localeCompare(b[0]);
    })
    .map(([currency]) => currency);

  const selected = sorted.slice(0, 3);
  for (const fallback of FALLBACK_CURRENCIES) {
    if (selected.length >= 3) break;
    if (!selected.includes(fallback)) selected.push(fallback);
  }
  return selected.slice(0, 3);
};

const buildChartOption = (
  buckets: StatsBucketSum[],
  grain: StatsGrain,
  currencies: string[]
): echarts.EChartsOption => {
  const labels = buckets.map((bucket) => formatBucketLabel(bucket.bucket_start, grain));

  const barSeries = currencies.map((currency, index) => ({
    type: 'bar' as const,
    name: currency.toUpperCase(),
    data: buckets.map((bucket) => getAmountForCurrency(bucket.amounts, currency)),
    yAxisIndex: 0,
    barMaxWidth: 26,
    itemStyle: { color: CURRENCY_COLORS[index % CURRENCY_COLORS.length] },
  }));

  const totalUsdSeries = {
    type: 'line' as const,
    name: 'Total USD',
    data: buckets.map((bucket) => Number(bucket.total_usd) || 0),
    yAxisIndex: 1,
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: { color: TOTAL_USD_LINE_COLOR },
    lineStyle: { color: TOTAL_USD_LINE_COLOR, width: 2 },
  };

  return {
    tooltip: {
      ...CHART_TOOLTIP_BASE,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const items = Array.isArray(params)
          ? (params as Array<{
              axisValueLabel: string;
              marker: string;
              seriesName: string;
              value: number;
            }>)
          : [];

        if (!items.length) return '';
        const lines = [items[0].axisValueLabel];

        for (const item of items) {
          const value = Number(item.value) || 0;
          const renderedValue =
            item.seriesName === 'Total USD' ? `$${formatNumber(value)}` : formatNumber(value);
          lines.push(`${item.marker}${item.seriesName}: ${renderedValue}`);
        }
        return lines.join('<br/>');
      },
    },
    legend: {
      top: 0,
      textStyle: CHART_LEGEND_TEXT,
    },
    grid: {
      left: 56,
      right: 60,
      top: 56,
      bottom: 40,
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: CHART_AXIS_LINE,
      axisLabel: CHART_AXIS_LABEL,
    },
    yAxis: [
      {
        type: 'value',
        axisLine: CHART_AXIS_LINE,
        axisLabel: { ...CHART_AXIS_LABEL, formatter: (value: number) => formatNumber(value) },
        splitLine: CHART_SPLIT_LINE,
      },
      {
        type: 'value',
        axisLine: CHART_AXIS_LINE,
        axisLabel: {
          ...CHART_AXIS_LABEL,
          formatter: (value: number) => `$${formatNumber(value)}`,
        },
        splitLine: { show: false },
      },
    ],
    series: [...barSeries, totalUsdSeries],
  };
};

type EChartsSurfaceProps = {
  option: echarts.EChartsOption;
};

const EChartsSurface = ({ option }: EChartsSurfaceProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chartRef.current?.dispose();
    chartRef.current = echarts.init(ref.current);
    resizeObserverRef.current = new ResizeObserver(() => chartRef.current?.resize());
    resizeObserverRef.current.observe(ref.current);

    return () => {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.setOption(option, true);
    chartRef.current.resize();
  }, [option]);

  return <div ref={ref} className="w-full h-[340px]" />;
};

export const Stats = () => {
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const [searchParams, setSearchParams] = useSearchParams();
  const now = useMemo(() => new Date(), []);
  const defaultFilters = useMemo<StatsFiltersValue>(
    () => ({
      ...getPresetRange(DEFAULT_PRESET, now),
      grain: DEFAULT_GRAIN,
      preset: DEFAULT_PRESET,
    }),
    [now]
  );
  const appliedFilters = useMemo<StatsFiltersValue>(() => {
    const presetParam = searchParams.get('preset');
    const parsedPreset = isStatsFilterPreset(presetParam) ? presetParam : DEFAULT_PRESET;
    const fallbackPreset = parsedPreset === 'custom' ? DEFAULT_PRESET : parsedPreset;
    const fallbackRange = getPresetRange(fallbackPreset, now);
    const parsedFrom = parseDateInput(searchParams.get('from'));
    const parsedTo = parseDateInput(searchParams.get('to'));
    const grainParam = searchParams.get('grain');

    const range =
      parsedFrom && parsedTo
        ? normalizeRange(formatDateInput(parsedFrom), formatDateInput(parsedTo))
        : fallbackRange;

    return {
      ...range,
      grain: isStatsGrain(grainParam) ? grainParam : DEFAULT_GRAIN,
      preset: parsedFrom && parsedTo ? parsedPreset : fallbackPreset,
    };
  }, [now, searchParams]);
  const [draftFilters, setDraftFilters] = useState<StatsFiltersValue>(appliedFilters);

  useEffect(() => {
    setDraftFilters(appliedFilters);
  }, [appliedFilters]);

  const isDirtyVsApplied = useMemo(
    () => !areStatsFiltersEqual(draftFilters, appliedFilters),
    [appliedFilters, draftFilters]
  );
  const isAtDefaults = useMemo(
    () => areStatsFiltersEqual(draftFilters, defaultFilters),
    [defaultFilters, draftFilters]
  );

  const applyFilters = useCallback(() => {
    const nextRange = normalizeRange(draftFilters.from, draftFilters.to);
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set('from', nextRange.from);
      params.set('to', nextRange.to);
      params.set('grain', draftFilters.grain);
      params.set('preset', draftFilters.preset);
      return params;
    });
  }, [draftFilters, setSearchParams]);

  const applyPreset = useCallback(
    (preset: Exclude<StatsFilterPreset, 'custom'>) => {
      const range = getPresetRange(preset, now);
      setDraftFilters((prev) => ({
        ...prev,
        ...normalizeRange(range.from, range.to),
        preset,
      }));
    },
    [now]
  );

  const handleFromChange = useCallback((value: string) => {
    const parsed = parseDateInput(value);
    if (!parsed) return;

    setDraftFilters((prev) => {
      const nextRange = normalizeRange(formatDateInput(parsed), prev.to);
      return {
        ...prev,
        ...nextRange,
        preset: 'custom',
      };
    });
  }, []);

  const handleToChange = useCallback((value: string) => {
    const parsed = parseDateInput(value);
    if (!parsed) return;

    setDraftFilters((prev) => {
      const nextRange = normalizeRange(prev.from, formatDateInput(parsed));
      return {
        ...prev,
        ...nextRange,
        preset: 'custom',
      };
    });
  }, []);

  const handleGrainChange = useCallback((value: string) => {
    setDraftFilters((prev) => ({
      ...prev,
      grain: value === 'week' ? 'week' : 'month',
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setDraftFilters(defaultFilters);
  }, [defaultFilters]);

  const residentFeeQuery = useQuery({
    queryKey: [
      'stats',
      'residentFee',
      appliedFilters.from,
      appliedFilters.to,
      appliedFilters.grain,
    ],
    queryFn: ({ signal }) =>
      getResidentFeeSum({
        timeframe_from: appliedFilters.from,
        timeframe_to: appliedFilters.to,
        grain: appliedFilters.grain,
        signal,
      }),
  });

  const transactionsQuery = useQuery({
    queryKey: [
      'stats',
      'transactions',
      appliedFilters.from,
      appliedFilters.to,
      appliedFilters.grain,
    ],
    queryFn: ({ signal }) =>
      getTransactionsSum({
        timeframe_from: appliedFilters.from,
        timeframe_to: appliedFilters.to,
        grain: appliedFilters.grain,
        signal,
      }),
  });

  const treasuriesQuery = useQuery({
    queryKey: ['treasuries', 'stats-summary'],
    queryFn: ({ signal }) => getTreasuries({ limit: 500, signal }),
  });

  const exchangeRatesQuery = useQuery({
    queryKey: ['exchange-rates', 'stats-summary'],
    queryFn: () => getExchangeRates(),
    staleTime: Infinity,
  });

  const residentFeeData = useMemo(() => residentFeeQuery.data ?? [], [residentFeeQuery.data]);
  const transactionsData = useMemo(() => transactionsQuery.data ?? [], [transactionsQuery.data]);
  const exchangeRates = useMemo(
    () => exchangeRatesQuery.data?.[0]?.currencies ?? [],
    [exchangeRatesQuery.data]
  );
  const selectedCurrencies = useMemo(
    () => pickTopCurrencies([...residentFeeData, ...transactionsData]),
    [residentFeeData, transactionsData]
  );

  const residentFeeOption = useMemo(
    () => buildChartOption(residentFeeData, appliedFilters.grain, selectedCurrencies),
    [appliedFilters.grain, residentFeeData, selectedCurrencies]
  );
  const transactionsOption = useMemo(
    () => buildChartOption(transactionsData, appliedFilters.grain, selectedCurrencies),
    [appliedFilters.grain, selectedCurrencies, transactionsData]
  );
  const residentFeeTotal = residentFeeData.reduce(
    (sum, bucket) => sum + (bucket.total_usd || 0),
    0
  );
  const transactionTotal = transactionsData.reduce(
    (sum, bucket) => sum + (bucket.total_usd || 0),
    0
  );
  const aggregatedTreasuryBalances = useMemo(() => {
    const totals: Record<string, number> = {};

    for (const treasury of treasuriesQuery.data?.items ?? []) {
      for (const [rawCurrency, rawAmount] of Object.entries(treasury.balances?.completed ?? {})) {
        const currency = rawCurrency.toUpperCase();
        const amount = Number(rawAmount) || 0;
        totals[currency] = (totals[currency] ?? 0) + amount;
      }
    }

    return totals;
  }, [treasuriesQuery.data?.items]);
  const currentBalances = useMemo(
    () =>
      TRACKED_BALANCE_CURRENCIES.reduce(
        (acc, currency) => ({
          ...acc,
          [currency]: aggregatedTreasuryBalances[currency] ?? 0,
        }),
        { GEL: 0, USD: 0, EUR: 0 } as Record<(typeof TRACKED_BALANCE_CURRENCIES)[number], number>
      ),
    [aggregatedTreasuryBalances]
  );
  const totalBalanceUsd = useMemo(() => {
    let total = 0;

    for (const [rawCurrency, rawAmount] of Object.entries(aggregatedTreasuryBalances)) {
      const amount = Number(rawAmount) || 0;
      if (amount === 0) continue;

      const converted = convertCurrencyAmount(amount, rawCurrency, 'USD', exchangeRates);
      if (converted == null) {
        return null;
      }

      total += converted;
    }

    return total;
  }, [aggregatedTreasuryBalances, exchangeRates]);
  const contributingFundsCount = useMemo(
    () =>
      (treasuriesQuery.data?.items ?? []).filter((treasury) =>
        Object.values(treasury.balances?.completed ?? {}).some((amount) => (Number(amount) || 0) !== 0)
      ).length,
    [treasuriesQuery.data?.items]
  );
  const balanceSummaryCaption = treasuriesQuery.isLoading
    ? 'Refreshing all hackerspace funds...'
    : totalBalanceUsd == null
      ? 'Some treasury currencies are missing exchange-rate coverage, so the USD total is unavailable.'
      : `${contributingFundsCount} fund${contributingFundsCount === 1 ? '' : 's'} included in the current snapshot.`;

  if (!actorEntity) {
    return null;
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="F0RTHSP4CE pulse"
        title="Stats"
        subtitle="Track hackerspace-wide funds, dues pressure, and overall money movement with one filter set and a shared chart language."
      />

      <AccentSurface p="xl">
        <Stack gap="lg">
          <Stack gap={6}>
            <Text className="app-kicker">General balance</Text>
            <Text className="app-section-title">Live funds snapshot across all treasuries</Text>
            <Text size="sm" className="app-muted-copy" maw={720}>
              Use this block as the quick operational read for total space funds before looking at dues or historical movement.
            </Text>
          </Stack>

          <Stack gap="xs">
            <Text size="xs" tt="uppercase" className="app-muted-copy">
              Total in USD
            </Text>
            <Text size="3rem" fw={900} lh={1}>
              {totalBalanceUsd == null ? 'Unavailable' : `$${formatNumber(totalBalanceUsd)}`}
            </Text>
            <Text size="sm" className="app-muted-copy">
              {balanceSummaryCaption}
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            {TRACKED_BALANCE_CURRENCIES.map((currency) => (
              <StatCard
                key={currency}
                label={`${currency} total`}
                value={formatNumber(currentBalances[currency])}
                caption="Across all funds"
              />
            ))}
          </SimpleGrid>
        </Stack>
      </AccentSurface>

      <FilterBar
        tone="accent"
        title="Filters"
        description="Set the reporting window and aggregation grain for dues and movement."
        action={
          <Group gap="xs">
            <Button variant="subtle" color="gray" disabled={isAtDefaults} onClick={resetFilters}>
              Reset
            </Button>
            <Button variant="default" disabled={!isDirtyVsApplied} onClick={applyFilters}>
              Apply
            </Button>
          </Group>
        }
      >
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
            <AppDateField
              label="From"
              value={draftFilters.from}
              onChange={handleFromChange}
            />
            <AppDateField
              label="To"
              value={draftFilters.to}
              onChange={handleToChange}
            />
            <div>
              <Text size="sm" fw={500} mb={6}>
                Grain
              </Text>
              <AppSegmentedControl
                fullWidth
                value={draftFilters.grain}
                onChange={handleGrainChange}
                data={[
                  { label: 'Week', value: 'week' },
                  { label: 'Month', value: 'month' },
                ]}
              />
            </div>
          </SimpleGrid>

          <Group gap="xs" wrap="wrap">
            {STATS_PRESET_OPTIONS.map((preset) => (
              <Button
                key={preset.key}
                variant={draftFilters.preset === preset.key ? 'filled' : 'light'}
                size="xs"
                onClick={() => applyPreset(preset.key)}
              >
                {preset.label}
              </Button>
            ))}
          </Group>
        </Stack>
      </FilterBar>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <StatCard
          label="Dues total"
          value={`$${formatNumber(residentFeeTotal)}`}
          caption={`${residentFeeData.length} bucket${residentFeeData.length === 1 ? '' : 's'} in range`}
        />
        <StatCard
          label="Transaction total"
          value={`$${formatNumber(transactionTotal)}`}
          caption={`${transactionsData.length} bucket${transactionsData.length === 1 ? '' : 's'} in range`}
        />
      </SimpleGrid>

      <ChartCard
        title="Dues volume"
        isLoading={residentFeeQuery.isLoading}
        isError={residentFeeQuery.isError}
        hasData={residentFeeData.length > 0}
        emptyMessage="No dues activity in the selected range."
        errorMessage="Failed to load dues insights."
        height="lg"
      >
        <EChartsSurface option={residentFeeOption} />
      </ChartCard>

      <ChartCard
        title="Money movement"
        isLoading={transactionsQuery.isLoading}
        isError={transactionsQuery.isError}
        hasData={transactionsData.length > 0}
        emptyMessage="No transaction activity in the selected range."
        errorMessage="Failed to load transaction insights."
        height="lg"
      >
        <EChartsSurface option={transactionsOption} />
      </ChartCard>
    </Stack>
  );
};
