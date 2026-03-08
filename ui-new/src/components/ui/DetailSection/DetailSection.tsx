import { Anchor, Box, Group, Paper, type PaperProps, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { TagList } from '../TagList';

type DetailSectionCardProps = PaperProps & {
  title: string;
  children: ReactNode;
};

type DetailItemProps = {
  label: string;
  children: ReactNode;
};

type DetailEntity = {
  id: number;
  name: string;
  tags?: { id: number; name: string }[];
};

type EntityInlineProps = {
  entity: DetailEntity;
  tagMode?: 'compact' | 'expanded';
  size?: 'xs' | 'sm' | 'md' | 'lg';
};

export const DetailSectionCard = ({ title, children, ...props }: DetailSectionCardProps) => (
  <Paper
    withBorder
    radius="xl"
    p="md"
    style={{
      background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.02))',
      borderColor: 'var(--app-border-subtle)',
    }}
    {...props}
  >
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" className="app-muted-copy">
        {title}
      </Text>
      {children}
    </Stack>
  </Paper>
);

export const DetailItem = ({ label, children }: DetailItemProps) => (
  <Stack gap={4}>
    <Text size="xs" tt="uppercase" className="app-muted-copy">
      {label}
    </Text>
    <Box>{children}</Box>
  </Stack>
);

export const EntityInline = ({ entity, tagMode = 'compact', size = 'sm' }: EntityInlineProps) => (
  <Group gap={6} align="center" wrap="wrap">
    <Anchor
      size={size}
      component={Link}
      to={`/profile/${entity.id}`}
      underline="hover"
      inherit
      aria-label={`Open ${entity.name} profile`}
    >
      {entity.name}
    </Anchor>
    {entity.tags?.length ? <TagList tags={entity.tags} mode={tagMode} /> : null}
  </Group>
);
