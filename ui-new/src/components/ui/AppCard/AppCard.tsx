import { Card, type CardProps } from '@mantine/core';
import type { ReactNode } from 'react';

type AppCardProps = CardProps & {
  children: ReactNode;
};

export const AppCard = ({ children, ...props }: AppCardProps) => {
  return (
    <Card withBorder radius="md" padding="lg" {...props}>
      {children}
    </Card>
  );
};
