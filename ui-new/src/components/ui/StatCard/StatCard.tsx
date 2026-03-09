import { Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { AppCard, type AppCardProps } from '../AppCard';

type StatCardProps = Omit<AppCardProps, 'children'> & {
  label: ReactNode;
  value: ReactNode;
  caption?: ReactNode;
  aside?: ReactNode;
};

export const StatCard = ({ label, value, caption, aside, ...props }: StatCardProps) => {
  return (
    <AppCard p="md" {...props}>
      <Stack gap={10}>
        <Group justify="space-between" align="start" gap="sm">
          <Text size="xs" tt="uppercase" className="app-muted-copy">
            {label}
          </Text>
          {aside}
        </Group>
        <Text className="app-stat-value">{value}</Text>
        {caption ? (
          <Text size="sm" className="app-muted-copy">
            {caption}
          </Text>
        ) : null}
      </Stack>
    </AppCard>
  );
};
