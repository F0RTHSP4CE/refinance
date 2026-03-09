import { Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';

type ModalStepHeaderProps = {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
};

export const ModalStepHeader = ({ eyebrow, title, description }: ModalStepHeaderProps) => {
  return (
    <Stack gap={6}>
      {eyebrow ? <Text className="app-kicker">{eyebrow}</Text> : null}
      {typeof title === 'string' ? <Text className="app-section-title">{title}</Text> : title}
      {description ? (
        <Text size="sm" className="app-muted-copy">
          {description}
        </Text>
      ) : null}
    </Stack>
  );
};
