import { Badge, type BadgeProps } from '@mantine/core';

export type StatusBadgeTone =
  | 'positive'
  | 'neutral'
  | 'success'
  | 'warning'
  | 'draft'
  | 'danger'
  | 'info';

type StatusBadgeProps = Omit<BadgeProps, 'color' | 'variant'> & {
  tone?: StatusBadgeTone;
};

const BASE_STYLE = {
  fontWeight: 800,
  letterSpacing: '0.05em',
};

const TONE_STYLES: Record<StatusBadgeTone, Record<string, string | number>> = {
  positive: {
    backgroundColor: 'rgba(54, 199, 123, 0.16)',
    color: 'var(--app-success)',
    border: '1px solid rgba(54, 199, 123, 0.28)',
    ...BASE_STYLE,
  },
  neutral: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    color: 'var(--app-text-primary)',
    border: '1px solid var(--app-border-subtle)',
    ...BASE_STYLE,
  },
  success: {
    backgroundColor: 'rgba(54, 199, 123, 0.16)',
    color: 'var(--app-success)',
    border: '1px solid rgba(54, 199, 123, 0.28)',
    ...BASE_STYLE,
  },
  warning: {
    backgroundColor: 'rgba(245, 183, 75, 0.16)',
    color: 'var(--app-warning)',
    border: '1px solid rgba(245, 183, 75, 0.28)',
    ...BASE_STYLE,
  },
  draft: {
    backgroundColor: 'rgba(88, 181, 255, 0.16)',
    color: 'var(--app-info)',
    border: '1px solid rgba(88, 181, 255, 0.26)',
    ...BASE_STYLE,
  },
  danger: {
    backgroundColor: 'rgba(255, 122, 120, 0.16)',
    color: 'var(--app-danger)',
    border: '1px solid rgba(255, 122, 120, 0.28)',
    ...BASE_STYLE,
  },
  info: {
    backgroundColor: 'rgba(155, 227, 65, 0.16)',
    color: 'var(--app-accent)',
    border: '1px solid rgba(155, 227, 65, 0.28)',
    ...BASE_STYLE,
  },
};

const resolveTone = (tone: StatusBadgeTone) => {
  if (tone === 'positive') return 'success';
  return tone;
};

export const StatusBadge = ({ tone = 'neutral', style, children, ...props }: StatusBadgeProps) => {
  const resolvedTone = resolveTone(tone);

  return (
    <Badge
      variant="filled"
      tt="uppercase"
      radius="xl"
      style={{
        ...TONE_STYLES[resolvedTone],
        ...style,
      }}
      {...props}
    >
      {children}
    </Badge>
  );
};
