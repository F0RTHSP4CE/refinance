import { Card, type CardProps } from '@mantine/core';
import type { ComponentPropsWithoutRef, CSSProperties, ReactNode } from 'react';

export type AppCardProps = Omit<CardProps, 'style'> &
  ComponentPropsWithoutRef<'div'> & {
    children: ReactNode;
    style?: CSSProperties;
  };

export const AppCard = ({ children, style, ...props }: AppCardProps) => {
  return (
    <Card
      withBorder
      radius="xl"
      padding="lg"
      style={{
        background: 'linear-gradient(180deg, rgba(28, 33, 40, 0.98), rgba(16, 19, 24, 0.98))',
        borderColor: 'var(--app-border-subtle)',
        boxShadow: 'var(--app-shadow-soft)',
        backdropFilter: 'blur(14px)',
        ...style,
      }}
      {...props}
    >
      {children}
    </Card>
  );
};
