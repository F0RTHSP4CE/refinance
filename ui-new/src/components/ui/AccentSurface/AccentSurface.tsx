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
        background:
          'radial-gradient(circle at top left, rgba(155, 227, 65, 0.14), transparent 34%), linear-gradient(160deg, rgba(19, 28, 34, 0.98), rgba(21, 29, 38, 0.95))',
        borderColor: 'rgba(155, 227, 65, 0.18)',
        ...style,
      }}
      {...props}
    >
      {children}
    </AppCard>
  );
};
