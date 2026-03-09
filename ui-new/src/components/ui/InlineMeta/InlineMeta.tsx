import { Box, Group } from '@mantine/core';
import type { ReactNode } from 'react';

type InlineMetaProps = {
  items: ReactNode[];
};

export const InlineMeta = ({ items }: InlineMetaProps) => {
  const visibleItems = items.filter(Boolean);

  if (visibleItems.length === 0) {
    return null;
  }

  return (
    <Group gap="xs" wrap="wrap">
      {visibleItems.map((item, index) => (
        <Box
          key={index}
          className="app-muted-copy"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            fontSize: 'var(--mantine-font-size-xs)',
            lineHeight: 'var(--mantine-line-height-xs)',
          }}
        >
          {item}
        </Box>
      ))}
    </Group>
  );
};
