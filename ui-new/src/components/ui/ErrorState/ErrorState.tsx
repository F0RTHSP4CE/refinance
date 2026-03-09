import { Button, Group, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { AppCard } from '../AppCard';

type ErrorStateProps = {
  title: string;
  description?: ReactNode;
  retryLabel?: string;
  onRetry?: () => void;
  compact?: boolean;
};

export const ErrorState = ({
  title,
  description,
  retryLabel = 'Try again',
  onRetry,
  compact = false,
}: ErrorStateProps) => {
  return (
    <AppCard p={compact ? 'md' : 'xl'}>
      <Stack align={compact ? 'flex-start' : 'center'} gap="sm">
        <ThemeIcon
          size={compact ? 42 : 54}
          radius="xl"
          variant="light"
          color="red"
          style={{
            background: 'rgba(255, 122, 120, 0.14)',
            color: 'var(--app-danger)',
            border: '1px solid rgba(255, 122, 120, 0.22)',
          }}
        >
          <IconAlertTriangle size={compact ? 20 : 24} />
        </ThemeIcon>
        <Stack gap={4} align={compact ? 'flex-start' : 'center'}>
          <Text fw={800}>{title}</Text>
          {description ? (
            <Text size="sm" ta={compact ? 'left' : 'center'} className="app-muted-copy">
              {description}
            </Text>
          ) : null}
        </Stack>
        {onRetry ? (
          <Group>
            <Button variant="default" onClick={onRetry}>
              {retryLabel}
            </Button>
          </Group>
        ) : null}
      </Stack>
    </AppCard>
  );
};
