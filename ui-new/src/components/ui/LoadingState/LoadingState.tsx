import { Group, Skeleton, Stack } from '@mantine/core';
import { AppCard } from '../AppCard';

type LoadingStateProps = {
  lines?: number;
  cards?: number;
  fullScreen?: boolean;
};

export const LoadingState = ({
  lines = 3,
  cards = 1,
  fullScreen = false,
}: LoadingStateProps) => {
  return (
    <Stack
      justify="center"
      gap="md"
      style={fullScreen ? { minHeight: '100vh', padding: '1rem' } : undefined}
    >
      {Array.from({ length: cards }).map((_, cardIndex) => (
        <AppCard key={cardIndex} p="lg">
          <Stack gap="sm">
            <Group justify="space-between">
              <Skeleton height={18} width="30%" radius="xl" />
              <Skeleton height={16} width={72} radius="xl" />
            </Group>
            {Array.from({ length: lines }).map((__, lineIndex) => (
              <Skeleton
                key={lineIndex}
                height={lineIndex === lines - 1 ? 42 : 14}
                width={lineIndex === lines - 1 ? '100%' : `${92 - lineIndex * 14}%`}
                radius="md"
              />
            ))}
          </Stack>
        </AppCard>
      ))}
    </Stack>
  );
};
