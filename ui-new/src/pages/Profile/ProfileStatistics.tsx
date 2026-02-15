import { AppCard } from '@/components/ui';
import { Button, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import * as echarts from 'echarts';
import { useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getEntityStatsBundle } from '@/api/stats';

const TIMEFRAME_OPTIONS = [3, 6, 12] as const;
const LIMIT_OPTIONS = [5, 8, 12] as const;

const formatUSD = (value: number) =>
  `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const hashString = (s: string) => {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash << 5) - hash + s.charCodeAt(i);
    hash |= 0;
  }
  return hash;
};

const colorFromId = (id: string | number, index: number) => {
  const key = String(id ?? `fallback-${index}`);
  const hash = Math.abs(hashString(key));
  const hue = (hash * 137.508) % 360;
  const sat = 55 + (hash % 30);
  const light = 42 + ((hash >> 3) % 28);
  return `hsl(${hue}, ${sat}%, ${light}%)`;
};

const AXIS_LINE = { lineStyle: { color: '#64748b' } };
const SPLIT_LINE = { lineStyle: { color: '#334155', type: 'dashed' as const } };
const AXIS_LABEL = { color: '#94a3b8' };

const PIE_LABEL = { show: false };
const PIE_LABEL_LINE = { show: false };

type ChartContainerProps = {
  children: React.ReactNode;
  title: string;
  height?: 'sm' | 'md';
};

const ChartContainer = ({ children, title, height = 'md' }: ChartContainerProps) => (
  <AppCard>
    <Text size="lg" fw={600} mb="md">
      {title}
    </Text>
    <div className={height === 'sm' ? 'w-full min-h-0 h-[240px]' : 'w-full min-h-0 h-[280px]'}>
      {children}
    </div>
  </AppCard>
);

type EChartsWrapperProps = {
  option: echarts.EChartsOption;
  height?: 'sm' | 'md';
};

const EChartsWrapper = ({ option, height = 'md' }: EChartsWrapperProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(ref.current);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
      chartRef.current = null;
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
      className={height === 'sm' ? 'w-full h-full min-h-0 h-[240px]' : 'w-full h-full min-h-0 h-[280px]'}
    />
  );
};

type ProfileStatisticsProps = {
  profileId: number;
};

export const ProfileStatistics = ({ profileId }: ProfileStatisticsProps) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const months = Math.min(12, Math.max(3, parseInt(searchParams.get('months') ?? '6', 10) || 6));
  const limit = Math.min(12, Math.max(5, parseInt(searchParams.get('limit') ?? '8', 10) || 8));

  const updateParam = useCallback(
    (key: 'months' | 'limit', value: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set(key, String(value));
        next.set('tab', 'statistics');
        return next;
      });
    },
    [setSearchParams]
  );

  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ['stats', profileId, months, limit],
    queryFn: () => getEntityStatsBundle(profileId, { months, limit }),
    enabled: !!profileId,
  });

  if (isLoading) {
    return (
      <Stack gap="lg" mt="md">
        <Text c="dimmed">Loading statistics...</Text>
      </Stack>
    );
  }

  if (isError || !stats) {
    return (
      <Stack gap="lg" mt="md">
        <Text c="dimmed">Failed to load statistics.</Text>
      </Stack>
    );
  }

  const balanceOption: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'time', axisLine: AXIS_LINE, axisLabel: AXIS_LABEL },
    yAxis: { type: 'value', axisLabel: { formatter: '${value}', ...AXIS_LABEL }, splitLine: SPLIT_LINE },
    series: [
      {
        type: 'line',
        name: 'Total (USD)',
        data: stats.balance_changes.map((d) => [d.day, d.total_usd]),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
      },
    ],
  };

  const moneyFlowOption: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { color: '#e2e8f0' } },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'time', axisLine: AXIS_LINE, axisLabel: AXIS_LABEL },
    yAxis: { type: 'value', axisLabel: { formatter: '${value}', ...AXIS_LABEL }, splitLine: SPLIT_LINE },
    series: [
      {
        type: 'bar',
        name: 'Income (USD)',
        data: stats.money_flow_by_day.map((d) => [d.day, d.incoming_total_usd]),
        itemStyle: { color: '#22c55e' },
      },
      {
        type: 'bar',
        name: 'Spending (USD)',
        data: stats.money_flow_by_day.map((d) => [d.day, -d.outgoing_total_usd]),
        itemStyle: { color: '#ef4444' },
      },
    ],
  };

  const topIncomingOption: echarts.EChartsOption | null = stats.top_incoming.length
    ? {
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        tooltip: {
          formatter: (p: unknown) => {
            const x = p as { name: string; value: number };
            return `${x.name}: ${formatUSD(x.value)}`;
          },
        },
        xAxis: {
          type: 'category',
          data: stats.top_incoming.map((d) => d.entity_name),
          axisLabel: { rotate: 30, ...AXIS_LABEL },
          axisLine: AXIS_LINE,
        },
        yAxis: { type: 'value', axisLabel: { formatter: '${value}', ...AXIS_LABEL }, splitLine: SPLIT_LINE },
        series: [
          {
            type: 'bar',
            data: stats.top_incoming.map((d, i) => ({
              value: d.total_usd,
              itemStyle: { color: colorFromId(d.entity_id, i) },
            })),
          },
        ],
      }
    : null;

  const topIncomingTagsOption: echarts.EChartsOption | null = stats.top_incoming_tags.length
    ? {
        tooltip: {
          formatter: (p: unknown) => {
            const x = p as { name: string; value: number; percent: number };
            return `${x.name}: ${formatUSD(x.value)} (${x.percent?.toFixed(1)}%)`;
          },
        },
        legend: { bottom: 0, textStyle: { color: '#e2e8f0' } },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            label: PIE_LABEL,
            labelLine: PIE_LABEL_LINE,
            data: stats.top_incoming_tags.map((d, i) => ({
              name: d.tag_name,
              value: d.total_usd,
              itemStyle: { color: colorFromId(d.tag_id, i) },
            })),
          },
        ],
      }
    : null;

  const topOutgoingOption: echarts.EChartsOption | null = stats.top_outgoing.length
    ? {
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        tooltip: {
          formatter: (p: unknown) => {
            const x = p as { name: string; value: number };
            return `${x.name}: ${formatUSD(x.value)}`;
          },
        },
        xAxis: {
          type: 'category',
          data: stats.top_outgoing.map((d) => d.entity_name),
          axisLabel: { rotate: 30, ...AXIS_LABEL },
          axisLine: AXIS_LINE,
        },
        yAxis: { type: 'value', axisLabel: { formatter: '${value}', ...AXIS_LABEL }, splitLine: SPLIT_LINE },
        series: [
          {
            type: 'bar',
            data: stats.top_outgoing.map((d, i) => ({
              value: d.total_usd,
              itemStyle: { color: colorFromId(d.entity_id, i) },
            })),
          },
        ],
      }
    : null;

  const topOutgoingTagsOption: echarts.EChartsOption | null = stats.top_outgoing_tags.length
    ? {
        tooltip: {
          formatter: (p: unknown) => {
            const x = p as { name: string; value: number; percent: number };
            return `${x.name}: ${formatUSD(x.value)} (${x.percent?.toFixed(1)}%)`;
          },
        },
        legend: { bottom: 0, textStyle: { color: '#e2e8f0' } },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            label: PIE_LABEL,
            labelLine: PIE_LABEL_LINE,
            data: stats.top_outgoing_tags.map((d, i) => ({
              name: d.tag_name,
              value: d.total_usd,
              itemStyle: { color: colorFromId(d.tag_id, i) },
            })),
          },
        ],
      }
    : null;

  return (
    <Stack gap="lg" mt="md">
      <AppCard>
        <Group gap="lg">
          <Group gap="xs">
            <Text size="sm" fw={500}>
              Timeframe:
            </Text>
            {TIMEFRAME_OPTIONS.map((m) => (
              <Button
                key={m}
                variant={months === m ? 'light' : 'subtle'}
                color={months === m ? 'green' : 'gray'}
                size="xs"
                onClick={() => updateParam('months', m)}
              >
                {m}m
              </Button>
            ))}
          </Group>
          <Text size="sm" c="dimmed">
            |
          </Text>
          <Group gap="xs">
            <Text size="sm" fw={500}>
              Top entries:
            </Text>
            {LIMIT_OPTIONS.map((l) => (
              <Button
                key={l}
                variant={limit === l ? 'light' : 'subtle'}
                color={limit === l ? 'green' : 'gray'}
                size="xs"
                onClick={() => updateParam('limit', l)}
              >
                {l}
              </Button>
            ))}
          </Group>
        </Group>
      </AppCard>

      <ChartContainer title="Balance Change by Day">
        <EChartsWrapper option={balanceOption} />
      </ChartContainer>

      <ChartContainer title="Income / Spending (USD) by Day / Month">
        <EChartsWrapper option={moneyFlowOption} />
      </ChartContainer>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Incoming Activity (last {months} months)
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
            <div className="w-full h-[280px]">
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
          Outgoing Activity (last {months} months)
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
            <div className="w-full h-[280px]">
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
