const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const hexToRgb = (hex: string) => {
  const normalized = hex.replace('#', '');
  const expanded =
    normalized.length === 3
      ? normalized
          .split('')
          .map((char) => `${char}${char}`)
          .join('')
      : normalized;

  const parsed = Number.parseInt(expanded, 16);
  return {
    r: (parsed >> 16) & 255,
    g: (parsed >> 8) & 255,
    b: parsed & 255,
  };
};

export const withAlpha = (hex: string, alpha: number) => {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${clamp(alpha, 0, 1)})`;
};

export const APP_CHART_COLORS = {
  lime: '#9be341',
  blue: '#58b5ff',
  amber: '#f5b74b',
  coral: '#ff7a78',
  slate: '#94a3b8',
  mint: '#36c77b',
  ink: '#dce4ef',
} as const;

export const TAG_COLOR_BY_NAME: Record<string, string> = {
  member: APP_CHART_COLORS.blue,
  resident: APP_CHART_COLORS.lime,
  'ex-resident': APP_CHART_COLORS.slate,
  guest: APP_CHART_COLORS.amber,
  hackerspace: APP_CHART_COLORS.lime,
  house: APP_CHART_COLORS.blue,
  operator: APP_CHART_COLORS.coral,
  system: APP_CHART_COLORS.slate,
  utilities: APP_CHART_COLORS.amber,
  food: APP_CHART_COLORS.amber,
  fee: APP_CHART_COLORS.coral,
  exchange: APP_CHART_COLORS.blue,
  donation: APP_CHART_COLORS.mint,
  deposit: APP_CHART_COLORS.blue,
  withdrawal: APP_CHART_COLORS.coral,
  automatic: APP_CHART_COLORS.slate,
  pos: APP_CHART_COLORS.blue,
  rent: APP_CHART_COLORS.coral,
} as const;

export const FALLBACK_TAG_COLORS = [
  APP_CHART_COLORS.blue,
  APP_CHART_COLORS.lime,
  APP_CHART_COLORS.amber,
  APP_CHART_COLORS.coral,
  APP_CHART_COLORS.slate,
  APP_CHART_COLORS.mint,
] as const;

export const SPLIT_PARTICIPANT_COLORS = [
  '#58b5ff',
  '#9be341',
  '#f5b74b',
  '#ff7a78',
  '#75d2ff',
  '#78d8a0',
  '#ffd17d',
  '#c0cad7',
] as const;

export const colorByStableIndex = (key: string | number, palette: readonly string[]) => {
  const normalized = String(key ?? '');
  let hash = 0;
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash << 5) - hash + normalized.charCodeAt(index);
    hash |= 0;
  }
  return palette[Math.abs(hash) % palette.length];
};
