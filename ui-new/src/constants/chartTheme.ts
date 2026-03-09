import type * as echarts from 'echarts';

export const CHART_AXIS_LINE = { lineStyle: { color: '#94a3b8' } } as const;

export const CHART_SPLIT_LINE = {
  lineStyle: { color: '#334155', type: 'dashed' as const },
} as const;

export const CHART_AXIS_LABEL = { color: '#cbd5e1' } as const;

export const CHART_LEGEND_TEXT = { color: '#e2e8f0' } as const;

export const CHART_TOOLTIP_TEXT = { color: '#e2e8f0' } as const;

export const CHART_TOOLTIP_BASE = {
  backgroundColor: 'rgba(10, 13, 17, 0.98)',
  borderColor: 'rgba(155, 227, 65, 0.22)',
  borderWidth: 1,
  textStyle: CHART_TOOLTIP_TEXT,
  extraCssText:
    'border-radius: 14px; box-shadow: 0 18px 40px rgba(0,0,0,0.28); backdrop-filter: blur(12px);',
} as const satisfies echarts.TooltipComponentOption;
