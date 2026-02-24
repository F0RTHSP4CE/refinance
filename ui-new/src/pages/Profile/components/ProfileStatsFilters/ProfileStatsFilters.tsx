import { Button, Group, SegmentedControl, SimpleGrid, Stack, Text, TextInput } from '@mantine/core';
import { useEffect, useMemo, useState } from 'react';
import { AppCard } from '@/components/ui';
import {
  PROFILE_PRESET_OPTIONS,
  PROFILE_STATS_LIMIT_OPTIONS,
  areProfileStatsFiltersEqual,
  formatDateInput,
  getPresetRange,
  normalizeRange,
  parseDateInput,
  type ProfileStatsFiltersValue,
  type ProfileStatsPreset,
} from './profileStatsFilterUtils';

type ProfileStatsFiltersProps = {
  appliedFilters: ProfileStatsFiltersValue;
  onApply: (nextFilters: ProfileStatsFiltersValue) => void;
};

export const ProfileStatsFilters = ({
  appliedFilters,
  onApply,
}: ProfileStatsFiltersProps) => {
  const [draftFilters, setDraftFilters] = useState<ProfileStatsFiltersValue>(
    appliedFilters
  );
  const [initialFilters] = useState<ProfileStatsFiltersValue>(appliedFilters);

  useEffect(() => {
    setDraftFilters(appliedFilters);
  }, [appliedFilters]);

  const isDirtyVsApplied = useMemo(
    () => !areProfileStatsFiltersEqual(draftFilters, appliedFilters),
    [appliedFilters, draftFilters]
  );

  const isDirtyVsInitial = useMemo(
    () => !areProfileStatsFiltersEqual(draftFilters, initialFilters),
    [draftFilters, initialFilters]
  );

  const handlePresetApply = (preset: Exclude<ProfileStatsPreset, 'custom'>) => {
    const range = getPresetRange(preset, new Date());
    setDraftFilters((prev) => ({
      ...prev,
      ...normalizeRange(range.from, range.to),
      preset,
    }));
  };

  const handleFromChange = (rawValue: string) => {
    const parsed = parseDateInput(rawValue);
    if (!parsed) return;

    const from = formatDateInput(parsed);
    const nextRange = normalizeRange(from, draftFilters.to);

    setDraftFilters((prev) => ({
      ...prev,
      ...nextRange,
      preset: 'custom',
    }));
  };

  const handleToChange = (rawValue: string) => {
    const parsed = parseDateInput(rawValue);
    if (!parsed) return;

    const to = formatDateInput(parsed);
    const nextRange = normalizeRange(draftFilters.from, to);

    setDraftFilters((prev) => ({
      ...prev,
      ...nextRange,
      preset: 'custom',
    }));
  };

  const handleApply = () => {
    const nextRange = normalizeRange(draftFilters.from, draftFilters.to);
    onApply({ ...draftFilters, ...nextRange });
  };

  return (
    <AppCard>
      <Stack gap="md">
        <Text size="lg" fw={600}>
          Statistics Filters
        </Text>

        <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
          <TextInput
            label="From"
            type="date"
            value={draftFilters.from}
            onChange={(event) => handleFromChange(event.currentTarget.value)}
          />
          <TextInput
            label="To"
            type="date"
            value={draftFilters.to}
            onChange={(event) => handleToChange(event.currentTarget.value)}
          />
          <div>
            <Text size="sm" fw={500} mb={6}>
              Grain
            </Text>
            <SegmentedControl
              fullWidth
              value={draftFilters.grain}
              onChange={(value) =>
                setDraftFilters((prev) => ({
                  ...prev,
                  grain: value === 'week' ? 'week' : 'month',
                }))
              }
              data={[
                { label: 'Week', value: 'week' },
                { label: 'Month', value: 'month' },
              ]}
            />
          </div>
        </SimpleGrid>

        <Group gap="xs" wrap="wrap">
          {PROFILE_PRESET_OPTIONS.map((preset) => (
            <Button
              key={preset.key}
              size="xs"
              variant={draftFilters.preset === preset.key ? 'filled' : 'light'}
              onClick={() => handlePresetApply(preset.key)}
            >
              {preset.label}
            </Button>
          ))}
        </Group>

        <Group gap="xs" wrap="wrap">
          <Text size="sm" fw={500}>
            Top entries:
          </Text>
          {PROFILE_STATS_LIMIT_OPTIONS.map((option) => (
            <Button
              key={option}
              size="xs"
              variant={draftFilters.limit === option ? 'filled' : 'subtle'}
              color={draftFilters.limit === option ? 'green' : 'gray'}
              onClick={() =>
                setDraftFilters((prev) => ({ ...prev, limit: option }))
              }
            >
              {option}
            </Button>
          ))}
        </Group>

        <Group justify="flex-end" gap="xs">
          {isDirtyVsInitial ? (
            <Button
              variant="subtle"
              color="gray"
              onClick={() => setDraftFilters(initialFilters)}
            >
              Reset
            </Button>
          ) : null}
          <Button disabled={!isDirtyVsApplied} onClick={handleApply}>
            Apply
          </Button>
        </Group>
      </Stack>
    </AppCard>
  );
};
