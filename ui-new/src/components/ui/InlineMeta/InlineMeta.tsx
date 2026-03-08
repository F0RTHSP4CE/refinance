import { Group, Text } from '@mantine/core';
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
        <Text key={index} size="xs" className="app-muted-copy">
          {item}
        </Text>
      ))}
    </Group>
  );
};
