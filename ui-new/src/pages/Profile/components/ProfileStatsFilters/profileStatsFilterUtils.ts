import type { StatsGrain } from '@/api/stats';

export type ProfileStatsPreset = 'last4w' | 'last3m' | 'last6m' | 'ytd' | 'custom';

export type ProfileStatsFiltersValue = {
  from: string;
  to: string;
  grain: StatsGrain;
  limit: number;
  preset: ProfileStatsPreset;
};

export const PROFILE_STATS_LIMIT_OPTIONS = [5, 8, 12] as const;

export const DEFAULT_PROFILE_STATS_GRAIN: StatsGrain = 'month';
export const DEFAULT_PROFILE_STATS_LIMIT = 8;
export const DEFAULT_PROFILE_STATS_PRESET: Exclude<ProfileStatsPreset, 'custom'> =
  'last3m';

export const PROFILE_PRESET_OPTIONS: Array<{
  key: Exclude<ProfileStatsPreset, 'custom'>;
  label: string;
}> = [
  { key: 'last4w', label: 'Last 4 weeks' },
  { key: 'last3m', label: 'Last 3 months' },
  { key: 'last6m', label: 'Last 6 months' },
  { key: 'ytd', label: 'Year to date' },
];

const pad = (value: number): string => String(value).padStart(2, '0');

export const formatDateInput = (dt: Date): string =>
  `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`;

export const parseDateInput = (value: string | null): Date | null => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) return null;
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year
    || parsed.getMonth() !== month - 1
    || parsed.getDate() !== day
  ) {
    return null;
  }
  return parsed;
};

export const subtractMonths = (dt: Date, months: number): Date => {
  const shifted = new Date(dt);
  const dayOfMonth = shifted.getDate();
  shifted.setDate(1);
  shifted.setMonth(shifted.getMonth() - months);
  const maxDay = new Date(
    shifted.getFullYear(),
    shifted.getMonth() + 1,
    0
  ).getDate();
  shifted.setDate(Math.min(dayOfMonth, maxDay));
  return shifted;
};

export const getPresetRange = (
  preset: Exclude<ProfileStatsPreset, 'custom'>,
  now: Date
): { from: string; to: string } => {
  const end = formatDateInput(now);

  if (preset === 'last4w') {
    const fromDate = new Date(now);
    fromDate.setDate(fromDate.getDate() - 27);
    return { from: formatDateInput(fromDate), to: end };
  }

  if (preset === 'last6m') {
    return { from: formatDateInput(subtractMonths(now, 6)), to: end };
  }

  if (preset === 'ytd') {
    return { from: `${now.getFullYear()}-01-01`, to: end };
  }

  return { from: formatDateInput(subtractMonths(now, 3)), to: end };
};

export const isProfileStatsPreset = (
  value: string | null
): value is ProfileStatsPreset =>
  value === 'last4w'
  || value === 'last3m'
  || value === 'last6m'
  || value === 'ytd'
  || value === 'custom';

export const isStatsGrain = (value: string | null): value is StatsGrain =>
  value === 'week' || value === 'month';

export const areProfileStatsFiltersEqual = (
  left: ProfileStatsFiltersValue,
  right: ProfileStatsFiltersValue
): boolean =>
  left.from === right.from
  && left.to === right.to
  && left.grain === right.grain
  && left.limit === right.limit
  && left.preset === right.preset;

export const normalizeRange = (
  from: string,
  to: string
): { from: string; to: string } => {
  if (from > to) {
    return { from: to, to };
  }
  return { from, to };
};
