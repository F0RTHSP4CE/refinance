import { Group } from '@mantine/core';
import { TagBadge } from '../TagBadge';

const MAX_VISIBLE = 3;

type Tag = { id: number; name: string };

type TagListProps = {
  tags: Tag[];
  /** When true, show all tags. When false (default), show first 3 + +N overflow. */
  showAll?: boolean;
};

export const TagList = ({ tags, showAll = false }: TagListProps) => {
  const visible = tags.slice(0, showAll ? tags.length : MAX_VISIBLE);
  const rest = tags.length - visible.length;

  return (
    <Group gap={6} style={{ flexWrap: 'wrap' }}>
      {visible.map((t) => (
        <TagBadge key={t.id} id={t.id} name={t.name} />
      ))}
      {!showAll && rest > 0 && <TagBadge id={0} name={`+${rest}`} overflow />}
    </Group>
  );
};
