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
  subtractMonths,
  type StatsFilterPreset,
  type StatsFiltersValue,
} from '@/components/ui/statsFilterUtils';

export type ProfileStatsPreset = StatsFilterPreset;

export type ProfileStatsFiltersValue = StatsFiltersValue & {
  limit: number;
};

export const PROFILE_STATS_LIMIT_OPTIONS = [5, 8, 12] as const;

export const DEFAULT_PROFILE_STATS_GRAIN = DEFAULT_STATS_GRAIN;
export const DEFAULT_PROFILE_STATS_LIMIT = 8;
export const DEFAULT_PROFILE_STATS_PRESET = DEFAULT_STATS_PRESET;

export const PROFILE_PRESET_OPTIONS = STATS_PRESET_OPTIONS;

export const isProfileStatsPreset = isStatsFilterPreset;

export const areProfileStatsFiltersEqual = (
  left: ProfileStatsFiltersValue,
  right: ProfileStatsFiltersValue
): boolean =>
  areStatsFiltersEqual(left, right) && left.limit === right.limit;

export { formatDateInput, getPresetRange, isStatsGrain, normalizeRange, parseDateInput, subtractMonths };
