import { Group } from '@mantine/core';
import { TagBadge } from '../TagBadge';

const MAX_VISIBLE = 3;

type Tag = { id: number; name: string };

type TagListProps = {
  tags: Tag[];
  mode?: 'compact' | 'expanded';
  /** Backwards-compatible alias for expanded mode. */
  showAll?: boolean;
};

export const TagList = ({ tags, mode, showAll = false }: TagListProps) => {
  const resolvedMode = mode ?? (showAll ? 'expanded' : 'compact');
  const visible = tags.slice(0, resolvedMode === 'expanded' ? tags.length : MAX_VISIBLE);
  const rest = tags.length - visible.length;

  return (
    <Group gap={6} style={{ flexWrap: 'wrap' }}>
      {visible.map((t) => (
        <TagBadge key={t.id} id={t.id} name={t.name} />
      ))}
      {resolvedMode === 'compact' && rest > 0 ? (
        <TagBadge id={0} name={`+${rest}`} overflow />
      ) : null}
    </Group>
  );
};
