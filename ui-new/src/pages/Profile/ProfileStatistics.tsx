import { AppCard, ChartCard, InlineState } from '@/components/ui';
import { SimpleGrid, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import * as echarts from 'echarts';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  getEntityStatsBundle,
  type EntityBalanceChangeByDay,
  type EntityMoneyFlowByDay,
} from '@/api/stats';
import {
  DEFAULT_PROFILE_STATS_GRAIN,
  DEFAULT_PROFILE_STATS_LIMIT,
  DEFAULT_PROFILE_STATS_PRESET,
  PROFILE_STATS_LIMIT_OPTIONS,
  ProfileStatsFilters,
  formatDateInput,
  getPresetRange,
  isProfileStatsPreset,
  isStatsGrain,
  parseDateInput,
  subtractMonths,
  type ProfileStatsFiltersValue,
  type ProfileStatsPreset,
} from './components/ProfileStatsFilters';
import { APP_CHART_COLORS, colorByStableIndex } from '@/constants/uiPalette';
import {
  CHART_AXIS_LABEL,
  CHART_AXIS_LINE,
  CHART_LEGEND_TEXT,
  CHART_SPLIT_LINE,
  CHART_TOOLTIP_BASE,
} from '@/constants/chartTheme';

const formatUSD = (value: number) =>
  `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const CHART_PALETTE = [
  APP_CHART_COLORS.blue,
  APP_CHART_COLORS.lime,
  APP_CHART_COLORS.amber,
  APP_CHART_COLORS.coral,
  APP_CHART_COLORS.slate,
  APP_CHART_COLORS.mint,
] as const;

const colorFromId = (id: string | number, index: number) =>
  colorByStableIndex(`${String(id ?? '')}:${index}`, CHART_PALETTE);

const PIE_LABEL = { show: false };
const PIE_LABEL_LINE = { show: false };

type EChartsWrapperProps = {
  option: echarts.EChartsOption;
  height?: 'sm' | 'md';
};

const EChartsWrapper = ({ option, height = 'md' }: EChartsWrapperProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!ref.current) return;

    if (chartRef.current) {
      chartRef.current.dispose();
      chartRef.current = null;
    }

    const chart = echarts.init(ref.current);
    chartRef.current = chart;

    resizeObserverRef.current = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserverRef.current.observe(ref.current);

    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (chartRef.current) {
        chartRef.current.dispose();
        chartRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.setOption(option, { replaceMerge: ['series'] });
      chartRef.current.resize();
    }
  }, [option]);

  return (
    <div
      ref={ref}
      className={
        height === 'sm' ? 'w-full h-full min-h-0 h-[240px]' : 'w-full h-full min-h-0 h-[280px]'
      }
    />
  );
};

const getIsoWeek = (dt: Date): { year: number; week: number } => {
  const utcDate = new Date(Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate()));
  const day = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  const week = Math.ceil((utcDate.getTime() - yearStart.getTime()) / 86400000 / 7 + 1);
  return { year: utcDate.getUTCFullYear(), week };
};

const pad = (value: number): string => String(value).padStart(2, '0');

const formatBucketLabel = (
  bucketStart: string,
  grain: ProfileStatsFiltersValue['grain']
): string => {
  const dt = parseDateInput(bucketStart);
  if (!dt) return bucketStart;

  if (grain === 'month') {
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}`;
  }

  const isoWeek = getIsoWeek(dt);
  return `${isoWeek.year}-W${pad(isoWeek.week)}`;
};

const getBucketStart = (day: string, grain: ProfileStatsFiltersValue['grain']): string => {
  const dt = parseDateInput(day);
  if (!dt) return day;

  if (grain === 'month') {
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-01`;
  }

  const bucketStart = new Date(dt);
  bucketStart.setDate(
    bucketStart.getDate() - bucketStart.getDay() + (bucketStart.getDay() === 0 ? -6 : 1)
  );
  return formatDateInput(bucketStart);
};

const aggregateBalanceByGrain = (
  rows: EntityBalanceChangeByDay[],
  grain: ProfileStatsFiltersValue['grain']
): Array<{ bucketStart: string; totalUsd: number }> => {
  const sorted = [...rows].sort((a, b) => a.day.localeCompare(b.day));
  const bucketToValue = new Map<string, number>();

  for (const row of sorted) {
    const bucketStart = getBucketStart(row.day, grain);
    bucketToValue.set(bucketStart, row.total_usd);
  }

  return Array.from(bucketToValue.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([bucketStart, totalUsd]) => ({ bucketStart, totalUsd }));
};

const aggregateMoneyFlowByGrain = (
  rows: EntityMoneyFlowByDay[],
  grain: ProfileStatsFiltersValue['grain']
): Array<{ bucketStart: string; incoming: number; outgoing: number }> => {
  const totals = new Map<string, { incoming: number; outgoing: number }>();

  for (const row of rows) {
    const bucketStart = getBucketStart(row.day, grain);
    const current = totals.get(bucketStart) ?? { incoming: 0, outgoing: 0 };
    current.incoming += row.incoming_total_usd;
    current.outgoing += row.outgoing_total_usd;
    totals.set(bucketStart, current);
  }

  return Array.from(totals.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([bucketStart, values]) => ({
      bucketStart,
      incoming: values.incoming,
      outgoing: values.outgoing,
    }));
};

type MonthlyMoneyFlowOverlay = {
  incomingByBucket: Array<number | null>;
  outgoingByBucket: Array<number | null>;
};

const aggregateMonthlyMoneyFlowOverlay = (
  rows: EntityMoneyFlowByDay[],
  grain: ProfileStatsFiltersValue['grain'],
  bucketStarts: string[]
): MonthlyMoneyFlowOverlay => {
  if (!rows.length || !bucketStarts.length) {
    return {
      incomingByBucket: [],
      outgoingByBucket: [],
    };
  }

  const sortedRows = [...rows].sort((a, b) => a.day.localeCompare(b.day));
  const firstVisibleDay = sortedRows[0]?.day ?? null;
  const firstVisibleBucketStart = firstVisibleDay ? getBucketStart(firstVisibleDay, grain) : null;
  const monthTotals = new Map<string, { incoming: number; outgoing: number; lastDay: string }>();

  for (const row of sortedRows) {
    const monthKey = row.day.slice(0, 7);
    const incoming = Number(row.incoming_total_usd || 0);
    const outgoing = Number(row.outgoing_total_usd || 0);
    const current = monthTotals.get(monthKey) ?? {
      incoming: 0,
      outgoing: 0,
      lastDay: row.day,
    };
    current.incoming += incoming;
    current.outgoing += outgoing;
    if (row.day > current.lastDay) {
      current.lastDay = row.day;
    }
    monthTotals.set(monthKey, current);
  }

  const linePointsByBucket = new Map<string, { incoming: number; outgoing: number }>();
  const sortedMonths = Array.from(monthTotals.keys()).sort((a, b) => a.localeCompare(b));
  for (const monthKey of sortedMonths) {
    const bucket = monthTotals.get(monthKey);
    if (!bucket) continue;
    const monthBucketStart = getBucketStart(bucket.lastDay, grain);
    linePointsByBucket.set(monthBucketStart, {
      incoming: bucket.incoming,
      outgoing: bucket.outgoing,
    });
  }

  if (
    firstVisibleBucketStart &&
    !linePointsByBucket.has(firstVisibleBucketStart) &&
    sortedMonths.length
  ) {
    const firstMonth = monthTotals.get(sortedMonths[0]);
    if (firstMonth) {
      linePointsByBucket.set(firstVisibleBucketStart, {
        incoming: firstMonth.incoming,
        outgoing: firstMonth.outgoing,
      });
    }
  }

  return {
    incomingByBucket: bucketStarts.map(
      (bucketStart) => linePointsByBucket.get(bucketStart)?.incoming ?? null
    ),
    outgoingByBucket: bucketStarts.map(
      (bucketStart) => linePointsByBucket.get(bucketStart)?.outgoing ?? null
    ),
  };
};

const getAppliedFilters = (searchParams: URLSearchParams, now: Date): ProfileStatsFiltersValue => {
  const defaultRange = getPresetRange(DEFAULT_PROFILE_STATS_PRESET, now);

  const fromRaw = searchParams.get('from');
  const toRaw = searchParams.get('to');
  const parsedFrom = parseDateInput(fromRaw);
  const parsedTo = parseDateInput(toRaw);

  const monthsRaw = Number.parseInt(searchParams.get('months') ?? '', 10);

  let from = defaultRange.from;
  let to = defaultRange.to;
  let preset: ProfileStatsPreset = DEFAULT_PROFILE_STATS_PRESET;

  if (parsedFrom && parsedTo) {
    from = formatDateInput(parsedFrom);
    to = formatDateInput(parsedTo);
    const presetParam = searchParams.get('preset');
    preset = isProfileStatsPreset(presetParam) ? presetParam : 'custom';
  } else if (!Number.isNaN(monthsRaw) && monthsRaw > 0) {
    from = formatDateInput(subtractMonths(now, monthsRaw));
    to = formatDateInput(now);
    if (monthsRaw === 3) {
      preset = 'last3m';
    } else if (monthsRaw === 6) {
      preset = 'last6m';
    } else {
      preset = 'custom';
    }
  }

  if (from > to) {
    from = to;
  }

  const grainParam = searchParams.get('grain');
  const grain = isStatsGrain(grainParam) ? grainParam : DEFAULT_PROFILE_STATS_GRAIN;

  const limitRaw = Number.parseInt(searchParams.get('limit') ?? '', 10);
  const limit = PROFILE_STATS_LIMIT_OPTIONS.includes(
    limitRaw as (typeof PROFILE_STATS_LIMIT_OPTIONS)[number]
  )
    ? limitRaw
    : DEFAULT_PROFILE_STATS_LIMIT;

  return {
    from,
    to,
    grain,
    limit,
    preset,
  };
};

type ProfileStatisticsProps = {
  profileId: number;
};

export const ProfileStatistics = ({ profileId }: ProfileStatisticsProps) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const now = useMemo(() => new Date(), []);

  const appliedFilters = useMemo(() => getAppliedFilters(searchParams, now), [now, searchParams]);

  const applyFilters = useCallback(
    (nextFilters: ProfileStatsFiltersValue) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('tab', 'statistics');
        next.set('from', nextFilters.from);
        next.set('to', nextFilters.to);
        next.set('grain', nextFilters.grain);
        next.set('limit', String(nextFilters.limit));
        next.set('preset', nextFilters.preset);
        next.delete('months');
        return next;
      });
    },
    [setSearchParams]
  );

  const {
    data: stats,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [
      'profile-stats',
      profileId,
      appliedFilters.from,
      appliedFilters.to,
      appliedFilters.limit,
    ],
    queryFn: ({ signal }) =>
      getEntityStatsBundle(profileId, {
        limit: appliedFilters.limit,
        timeframe_from: appliedFilters.from,
        timeframe_to: appliedFilters.to,
        signal,
      }),
    enabled: !!profileId,
  });

  if (isLoading) {
    return (
      <Stack gap="lg" mt="md">
        <InlineState kind="loading" cards={2} lines={4} />
      </Stack>
    );
  }

  if (isError || !stats) {
    return (
      <Stack gap="lg" mt="md">
        <InlineState
          kind="error"
          title="Stats could not be loaded"
          description="Profile stats are unavailable right now."
        />
      </Stack>
    );
  }

  const bucketedBalance = aggregateBalanceByGrain(stats.balance_changes, appliedFilters.grain);
  const bucketedMoneyFlow = aggregateMoneyFlowByGrain(
    stats.money_flow_by_day,
    appliedFilters.grain
  );
  const moneyFlowBucketStarts = bucketedMoneyFlow.map((row) => row.bucketStart);
  const monthlyMoneyFlowOverlay = aggregateMonthlyMoneyFlowOverlay(
    stats.money_flow_by_day,
    appliedFilters.grain,
    moneyFlowBucketStarts
  );

  const balanceOption: echarts.EChartsOption = {
    tooltip: { ...CHART_TOOLTIP_BASE, trigger: 'axis' },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      axisLine: CHART_AXIS_LINE,
      axisLabel: CHART_AXIS_LABEL,
      data: bucketedBalance.map((row) => formatBucketLabel(row.bucketStart, appliedFilters.grain)),
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '${value}', ...CHART_AXIS_LABEL },
      splitLine: CHART_SPLIT_LINE,
      axisLine: CHART_AXIS_LINE,
    },
    series: [
      {
        type: 'line',
        name: 'Total (USD)',
        data: bucketedBalance.map((row) => row.totalUsd),
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        itemStyle: { color: APP_CHART_COLORS.blue },
        lineStyle: { color: APP_CHART_COLORS.blue, width: 2 },
      },
    ],
  };

  const moneyFlowOption: echarts.EChartsOption = {
    tooltip: { ...CHART_TOOLTIP_BASE, trigger: 'axis' },
    legend: { bottom: 0, textStyle: CHART_LEGEND_TEXT },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      axisLine: CHART_AXIS_LINE,
      axisLabel: CHART_AXIS_LABEL,
      data: moneyFlowBucketStarts.map((bucketStart) =>
        formatBucketLabel(bucketStart, appliedFilters.grain)
      ),
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '${value}', ...CHART_AXIS_LABEL },
      splitLine: CHART_SPLIT_LINE,
      axisLine: CHART_AXIS_LINE,
    },
    series: [
      {
        type: 'bar',
        name: 'Income (USD)',
        data: bucketedMoneyFlow.map((row) => row.incoming),
        itemStyle: { color: APP_CHART_COLORS.mint },
      },
      {
        type: 'bar',
        name: 'Spending (USD)',
        data: bucketedMoneyFlow.map((row) => row.outgoing),
        itemStyle: { color: APP_CHART_COLORS.coral },
      },
      {
        type: 'line',
        name: 'Monthly Income (USD)',
        data: monthlyMoneyFlowOverlay.incomingByBucket,
        connectNulls: true,
        smooth: 0.15,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: APP_CHART_COLORS.lime },
        lineStyle: { color: APP_CHART_COLORS.lime, width: 2 },
        z: 10,
      },
      {
        type: 'line',
        name: 'Monthly Spending (USD)',
        data: monthlyMoneyFlowOverlay.outgoingByBucket,
        connectNulls: true,
        smooth: 0.15,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: APP_CHART_COLORS.coral },
        lineStyle: { color: APP_CHART_COLORS.coral, width: 2 },
        z: 10,
      },
    ],
  };

  const topIncomingOption: echarts.EChartsOption | null = stats.top_incoming.length
    ? {
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true,
        },
        tooltip: {
          ...CHART_TOOLTIP_BASE,
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (p: unknown) => {
            const params = p as Array<{ name: string; value: number }>;
            const first = params[0];
            return `${first.name}: ${formatUSD(first.value)}`;
          },
        },
        xAxis: {
          type: 'category',
          data: stats.top_incoming.map((item) => item.entity_name),
          axisLabel: { rotate: 30, ...CHART_AXIS_LABEL },
          axisLine: CHART_AXIS_LINE,
        },
        yAxis: {
          type: 'value',
          axisLabel: { formatter: '${value}', ...CHART_AXIS_LABEL },
          splitLine: CHART_SPLIT_LINE,
          axisLine: CHART_AXIS_LINE,
        },
        series: [
          {
            type: 'bar',
            data: stats.top_incoming.map((item, index) => ({
              value: item.total_usd,
              itemStyle: { color: colorFromId(item.entity_id, index) },
            })),
          },
        ],
      }
    : null;

  const topIncomingTagsOption: echarts.EChartsOption | null = stats.top_incoming_tags.length
    ? {
        tooltip: {
          ...CHART_TOOLTIP_BASE,
          formatter: (p: unknown) => {
            const point = p as {
              name: string;
              value: number;
              percent: number;
            };
            return `${point.name}: ${formatUSD(point.value)} (${point.percent?.toFixed(1)}%)`;
          },
        },
        legend: { bottom: '5%', textStyle: CHART_LEGEND_TEXT },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '45%'],
            label: PIE_LABEL,
            labelLine: PIE_LABEL_LINE,
            data: stats.top_incoming_tags.map((item, index) => ({
              name: item.tag_name,
              value: item.total_usd,
              itemStyle: { color: colorFromId(item.tag_id, index) },
            })),
          },
        ],
      }
    : null;

  const topOutgoingOption: echarts.EChartsOption | null = stats.top_outgoing.length
    ? {
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true,
        },
        tooltip: {
          ...CHART_TOOLTIP_BASE,
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (p: unknown) => {
            const params = p as Array<{ name: string; value: number }>;
            const first = params[0];
            return `${first.name}: ${formatUSD(first.value)}`;
          },
        },
        xAxis: {
          type: 'category',
          data: stats.top_outgoing.map((item) => item.entity_name),
          axisLabel: { rotate: 30, ...CHART_AXIS_LABEL },
          axisLine: CHART_AXIS_LINE,
        },
        yAxis: {
          type: 'value',
          axisLabel: { formatter: '${value}', ...CHART_AXIS_LABEL },
          splitLine: CHART_SPLIT_LINE,
          axisLine: CHART_AXIS_LINE,
        },
        series: [
          {
            type: 'bar',
            data: stats.top_outgoing.map((item, index) => ({
              value: item.total_usd,
              itemStyle: { color: colorFromId(item.entity_id, index) },
            })),
          },
        ],
      }
    : null;

  const topOutgoingTagsOption: echarts.EChartsOption | null = stats.top_outgoing_tags.length
    ? {
        tooltip: {
          ...CHART_TOOLTIP_BASE,
          formatter: (p: unknown) => {
            const point = p as {
              name: string;
              value: number;
              percent: number;
            };
            return `${point.name}: ${formatUSD(point.value)} (${point.percent?.toFixed(1)}%)`;
          },
        },
        legend: { bottom: '5%', textStyle: CHART_LEGEND_TEXT },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '45%'],
            label: PIE_LABEL,
            labelLine: PIE_LABEL_LINE,
            data: stats.top_outgoing_tags.map((item, index) => ({
              name: item.tag_name,
              value: item.total_usd,
              itemStyle: { color: colorFromId(item.tag_id, index) },
            })),
          },
        ],
      }
    : null;

  return (
    <Stack gap="lg" mt="md">
      <ProfileStatsFilters
        key={`profile-stats-filters-${profileId}`}
        appliedFilters={appliedFilters}
        onApply={applyFilters}
      />

      <ChartCard
        title="Balance change"
        description="How this profile's USD-equivalent balance moved across the selected range."
      >
        <EChartsWrapper option={balanceOption} />
      </ChartCard>

      <ChartCard
        title="Income and spending"
        description="Incoming and outgoing movement with monthly overlays for easier trend reading."
      >
        <EChartsWrapper option={moneyFlowOption} />
      </ChartCard>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Incoming Activity
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          {topIncomingOption ? (
            <div className="w-full h-[280px]">
              <Text size="sm" fw={500} mb="xs">
                Top Income Sources
              </Text>
              <EChartsWrapper option={topIncomingOption} height="sm" />
            </div>
          ) : (
            <Text size="sm" c="dimmed">
              No incoming transactions in the selected timeframe.
            </Text>
          )}
          {topIncomingTagsOption ? (
            <div className="w-full h-[320px]">
              <Text size="sm" fw={500} mb="xs">
                Top Incoming Tags
              </Text>
              <EChartsWrapper option={topIncomingTagsOption} height="sm" />
            </div>
          ) : (
            <Text size="sm" c="dimmed">
              No tagged incoming activity in the selected timeframe.
            </Text>
          )}
        </SimpleGrid>
      </AppCard>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Outgoing Activity
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          {topOutgoingOption ? (
            <div className="w-full h-[280px]">
              <Text size="sm" fw={500} mb="xs">
                Top Expense Destinations
              </Text>
              <EChartsWrapper option={topOutgoingOption} height="sm" />
            </div>
          ) : (
            <Text size="sm" c="dimmed">
              No outgoing transactions in the selected timeframe.
            </Text>
          )}
          {topOutgoingTagsOption ? (
            <div className="w-full h-[320px]">
              <Text size="sm" fw={500} mb="xs">
                Top Outgoing Tags
              </Text>
              <EChartsWrapper option={topOutgoingTagsOption} height="sm" />
            </div>
          ) : (
            <Text size="sm" c="dimmed">
              No tagged outgoing activity in the selected timeframe.
            </Text>
          )}
        </SimpleGrid>
      </AppCard>
    </Stack>
  );
};
