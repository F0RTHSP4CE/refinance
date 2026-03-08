import type { ReactNode } from 'react';
import type { CardProps } from '@mantine/core';
import { AppCard } from '../AppCard';

type AccentSurfaceProps = CardProps & {
  children: ReactNode;
};

export const AccentSurface = ({ children, style, ...props }: AccentSurfaceProps) => {
  return (
    <AppCard
      style={{
        background: 'linear-gradient(120deg, rgba(14, 165, 233, 0.08), rgba(34, 197, 94, 0.08))',
        borderColor: 'rgba(15, 23, 42, 0.12)',
        ...style,
      }}
      {...props}
    >
      {children}
    </AppCard>
  );
};
