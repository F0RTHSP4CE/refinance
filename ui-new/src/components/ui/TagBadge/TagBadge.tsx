import { Box } from '@mantine/core';
import { FALLBACK_TAG_COLORS, TAG_COLOR_BY_NAME, colorByStableIndex, withAlpha } from '@/constants/uiPalette';

type TagBadgeProps = {
  id: number;
  name: string;
  /** Gray style for +N overflow badge */
  overflow?: boolean;
};

export const TagBadge = ({ id, name, overflow }: TagBadgeProps) => {
  const normalizedName = name.trim().toLowerCase();
  const baseColor =
    TAG_COLOR_BY_NAME[normalizedName] ?? colorByStableIndex(`${normalizedName}:${id}`, FALLBACK_TAG_COLORS);
  const color = overflow ? 'var(--app-text-secondary)' : baseColor;
  const backgroundColor = overflow ? 'rgba(255, 255, 255, 0.04)' : withAlpha(baseColor, 0.16);
  const borderColor = overflow ? 'var(--app-border-subtle)' : withAlpha(baseColor, 0.34);

  return (
    <Box
      component="span"
      style={{
        display: 'inline-block',
        padding: '0.22rem 0.48rem',
        border: `1px solid ${borderColor}`,
        borderRadius: '999px',
        color,
        backgroundColor,
        verticalAlign: 'baseline',
        fontSize: '0.78rem',
        fontWeight: 700,
        letterSpacing: '0.01em',
      }}
    >
      {name}
    </Box>
  );
};
