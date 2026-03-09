import { Group, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  variant?: 'default' | 'hero';
};

export const PageHeader = ({
  eyebrow,
  title,
  subtitle,
  actions,
  variant = 'default',
}: PageHeaderProps) => {
  return (
    <Group justify="space-between" align={variant === 'hero' ? 'start' : 'end'} gap="md" wrap="wrap">
      <Stack gap={6}>
        {eyebrow ? <Text className="app-kicker">{eyebrow}</Text> : null}
        <Title
          order={1}
          className={variant === 'hero' ? 'app-hero-title' : 'app-page-title'}
          maw={variant === 'hero' ? 920 : 760}
        >
          {title}
        </Title>
        {subtitle ? (
          <Text size={variant === 'hero' ? 'md' : 'sm'} maw={variant === 'hero' ? 820 : 720} className="app-muted-copy">
            {subtitle}
          </Text>
        ) : null}
      </Stack>
      {actions ? <Group gap="sm">{actions}</Group> : null}
    </Group>
  );
};
