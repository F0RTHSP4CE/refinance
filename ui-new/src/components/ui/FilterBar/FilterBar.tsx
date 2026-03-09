import { Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { AppCard, type AppCardProps } from '../AppCard';

type FilterBarProps = AppCardProps & {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  resultSummary?: ReactNode;
  tone?: 'accent' | 'default';
};

export const FilterBar = ({
  title,
  description,
  action,
  resultSummary,
  tone = 'accent',
  children,
  style,
  className,
  ...props
}: FilterBarProps) => {
  return (
    <AppCard
      p={tone === 'accent' ? 'lg' : 'md'}
      className={className}
      style={{
        background:
          tone === 'accent'
            ? 'var(--app-panel-surface)'
            : 'var(--app-surface-2)',
        borderColor:
          tone === 'accent' ? 'var(--app-panel-border)' : 'var(--app-border-subtle)',
        boxShadow: tone === 'accent' ? 'var(--app-panel-shadow)' : undefined,
        ...style,
      }}
      {...props}
    >
      <Stack gap="md">
        {title || description || action ? (
          <Group justify="space-between" align="start" gap="md" wrap="wrap">
            <Stack gap={4}>
              {typeof title === 'string' ? <Text className="app-kicker">{title}</Text> : title}
              {description ? (
                <Text size="sm" className="app-muted-copy">
                  {description}
                </Text>
              ) : null}
              {resultSummary ? (
                <Text size="sm" fw={600}>
                  {resultSummary}
                </Text>
              ) : null}
            </Stack>
            {action}
          </Group>
        ) : null}
        {children}
      </Stack>
    </AppCard>
  );
};
