import { Box, Group, Stack, Text } from '@mantine/core';
import type { Split } from '@/types/api';
import { formatSplitMoney, getSplitParticipantColor, getSplitParticipantShare } from './splitUtils';

type SplitProgressBarProps = {
  split: Split;
  height?: number;
  showLegend?: boolean;
};

export const SplitProgressBar = ({
  split,
  height = 12,
  showLegend = false,
}: SplitProgressBarProps) => {
  return (
    <Stack gap={showLegend ? 'xs' : 0}>
      <Group
        gap={0}
        wrap="nowrap"
        style={{
          borderRadius: 999,
          overflow: 'hidden',
          background: 'rgba(148, 163, 184, 0.16)',
          minHeight: height,
        }}
      >
        {split.participants.length ? (
          split.participants.map((participant) => {
            const share = Number(getSplitParticipantShare(participant, split));
            const width = Number(split.amount) > 0 ? (share / Number(split.amount)) * 100 : 0;

            return (
              <Box
                key={participant.entity.id}
                style={{
                  width: `${Math.max(width, 0)}%`,
                  minHeight: height,
                  background: getSplitParticipantColor(participant.entity.id),
                  opacity: split.performed ? 0.45 : 1,
                }}
              />
            );
          })
        ) : (
          <Box style={{ width: '100%', minHeight: height }} />
        )}
      </Group>

      {showLegend ? (
        split.participants.length ? (
          <Group gap="xs" wrap="wrap">
            {split.participants.map((participant) => (
              <Group key={participant.entity.id} gap={6} wrap="nowrap">
                <Box
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 999,
                    background: getSplitParticipantColor(participant.entity.id),
                    flexShrink: 0,
                  }}
                />
                <Text size="sm">
                  {participant.entity.name} ·{' '}
                  {formatSplitMoney(getSplitParticipantShare(participant, split))}{' '}
                  {split.currency.toUpperCase()}
                </Text>
              </Group>
            ))}
          </Group>
        ) : (
          <Text size="sm" c="dimmed">
            No participants yet.
          </Text>
        )
      ) : null}
    </Stack>
  );
};
