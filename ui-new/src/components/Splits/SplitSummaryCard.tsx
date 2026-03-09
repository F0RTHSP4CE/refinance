import { Button, Group, Stack, Text } from '@mantine/core';
import { AppCard, StatusBadge, TagList } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';
import type { Split } from '@/types/api';
import type { KeyboardEvent } from 'react';
import { SplitProgressBar } from './SplitProgressBar';
import {
  formatSplitMoney,
  getDisplayedCollectedAmount,
  getSplitDisplayName,
  getSplitStatsLabel,
} from './splitUtils';

type SplitSummaryCardProps = {
  split: Split;
  onOpen: (splitId: number) => void;
  onJoin: (splitId: number) => void;
};

export const SplitSummaryCard = ({ split, onOpen, onJoin }: SplitSummaryCardProps) => {
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const isJoined =
    actorEntity != null &&
    split.participants.some((participant) => participant.entity.id === actorEntity.id);
  const statsLabel = getSplitStatsLabel(split);
  const openSplit = () => onOpen(split.id);
  const handleCardKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openSplit();
    }
  };

  return (
    <AppCard
      h="100%"
      role="button"
      tabIndex={0}
      aria-label={`Open ${getSplitDisplayName(split)}`}
      onClick={openSplit}
      onKeyDown={handleCardKeyDown}
      style={{
        background: split.performed
          ? 'rgba(148, 163, 184, 0.08)'
          : 'linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))',
        borderColor: split.performed ? 'rgba(148, 163, 184, 0.24)' : 'rgba(14, 165, 233, 0.14)',
        transition: 'transform 120ms ease, border-color 120ms ease',
        cursor: 'pointer',
      }}
    >
        <Stack gap="md" h="100%">
          <Group justify="space-between" align="flex-start" gap="sm">
            <Stack gap={4}>
              <Text fw={700} size="lg" style={{ lineHeight: 1.2 }}>
                {getSplitDisplayName(split)}
              </Text>
              <Text size="sm" c="dimmed">
                To {split.recipient_entity.name} · By {split.actor_entity.name}
              </Text>
            </Stack>
            <Stack gap={6} align="flex-end">
              <Text size="xs" c="dimmed">
                #{split.id}
              </Text>
              <StatusBadge tone={split.performed ? 'success' : 'info'}>
                {split.performed ? 'done' : 'active'}
              </StatusBadge>
            </Stack>
          </Group>

          <Stack gap={4}>
            <Text size="xl" fw={700}>
              {getDisplayedCollectedAmount(split)} / {formatSplitMoney(split.amount)}{' '}
              {split.currency.toUpperCase()}
            </Text>
            <Text size="sm" c="dimmed">
              {split.participants.length} participant{split.participants.length === 1 ? '' : 's'}
              {statsLabel ? ` · ${statsLabel}` : ''}
            </Text>
          </Stack>

          <SplitProgressBar split={split} />

          <Group justify="space-between" align="flex-end" mt="auto">
            <Stack gap={4}>
              {split.tags.length ? <TagList tags={split.tags} mode="compact" /> : null}
              {!split.performed && isJoined ? (
                <Text size="sm" c="dimmed">
                  You are already participating.
                </Text>
              ) : null}
            </Stack>

            {!split.performed && !isJoined ? (
              <Button
                size="xs"
                variant="default"
                onClick={(event) => {
                  event.stopPropagation();
                  onJoin(split.id);
                }}
                onKeyDown={(event) => event.stopPropagation()}
              >
                Join
              </Button>
            ) : null}
          </Group>
        </Stack>
    </AppCard>
  );
};
