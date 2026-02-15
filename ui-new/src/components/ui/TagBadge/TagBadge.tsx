import { Box } from '@mantine/core';

const TAG_COLOR_FORMULA = (id: number) => `hsl(${(id * 41.9) % 360}, 66%, 44%)`;

type TagBadgeProps = {
  id: number;
  name: string;
  /** Gray style for +N overflow badge */
  overflow?: boolean;
};

export const TagBadge = ({ id, name, overflow }: TagBadgeProps) => {
  const hue = (id * 41.9) % 360;
  const color = overflow ? 'var(--mantine-color-gray-5)' : TAG_COLOR_FORMULA(id);
  const backgroundColor = overflow
    ? 'transparent'
    : `hsla(${hue}, 66%, 44%, 0.25)`;

  return (
    <Box
      component="span"
      style={{
        display: 'inline-block',
        padding: '0.15rem 0.35rem',
        border: `1px solid ${color}`,
        borderRadius: '0.2rem',
        color,
        backgroundColor,
        opacity: 0.8,
        verticalAlign: 'baseline',
      }}
    >
      {name}
    </Box>
  );
};
