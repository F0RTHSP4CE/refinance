import { Stack, Text, ThemeIcon } from '@mantine/core';
import { IconInbox } from '@tabler/icons-react';
import type { ReactNode } from 'react';

const DEFAULT_EMPTY_STATE_DESCRIPTION = 'Nothing to show here yet.';

type EmptyStateProps = {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  compact?: boolean;
};

export const EmptyState = ({
  title,
  description,
  action,
  icon,
  compact = false,
}: EmptyStateProps) => {
  const resolvedDescription = description ?? DEFAULT_EMPTY_STATE_DESCRIPTION;

  return (
    <Stack
      align={compact ? 'flex-start' : 'center'}
      gap="sm"
      py={compact ? 0 : 'xl'}
      maw={compact ? undefined : 460}
    >
      <ThemeIcon
        size={compact ? 40 : 52}
        radius="xl"
        variant="light"
        color="gray"
        style={{
          background: 'rgba(255, 255, 255, 0.06)',
          color: 'var(--app-accent)',
          border: '1px solid var(--app-border-subtle)',
        }}
      >
        {icon ?? <IconInbox size={compact ? 18 : 24} />}
      </ThemeIcon>
      <Stack gap={4} align={compact ? 'flex-start' : 'center'}>
        <Text fw={700}>{title}</Text>
        <Text size="sm" ta={compact ? 'left' : 'center'} className="app-muted-copy">
          {resolvedDescription}
        </Text>
      </Stack>
      {action}
    </Stack>
  );
};
