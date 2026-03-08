import { Badge, type BadgeProps } from '@mantine/core';

export type StatusBadgeTone = 'positive' | 'neutral';

type StatusBadgeProps = Omit<BadgeProps, 'color' | 'variant'> & {
  tone?: StatusBadgeTone;
};

const POSITIVE_STYLE = {
  backgroundColor: 'var(--mantine-color-black)',
  color: 'var(--mantine-color-white)',
  border: '1px solid var(--mantine-color-black)',
  fontWeight: 800,
  letterSpacing: '0.05em',
};

const NEUTRAL_STYLE = {
  backgroundColor: 'var(--mantine-color-white)',
  color: 'var(--mantine-color-black)',
  border: '1px solid var(--mantine-color-black)',
  fontWeight: 800,
  letterSpacing: '0.05em',
};

export const StatusBadge = ({ tone = 'neutral', style, children, ...props }: StatusBadgeProps) => {
  return (
    <Badge
      variant="filled"
      tt="uppercase"
      style={{
        ...(tone === 'positive' ? POSITIVE_STYLE : NEUTRAL_STYLE),
        ...style,
      }}
      {...props}
    >
      {children}
    </Badge>
  );
};
