import { Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { AppCard, type AppCardProps } from '../AppCard/AppCard';

type SectionCardProps = AppCardProps & {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
};

export const SectionCard = ({
  title,
  description,
  action,
  children,
  ...props
}: SectionCardProps) => {
  return (
    <AppCard {...props}>
      <Stack gap="md">
        {title || description || action ? (
          <Group justify="space-between" align="start" gap="md" wrap="wrap">
            <Stack gap={4}>
              {typeof title === 'string' ? <Text className="app-section-title">{title}</Text> : title}
              {description ? (
                <Text size="sm" className="app-muted-copy">
                  {description}
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
