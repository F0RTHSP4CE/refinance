import { Anchor, Group, Text, Tooltip } from '@mantine/core';
import type { SyntheticEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  AmountCurrency,
  RelativeDate,
  TagList,
  type DataTableColumn,
} from '@/components/ui';
import type { Transaction } from '@/types/api';

const COMMENT_PREVIEW_LENGTH = 30;

const stopRowClickPropagation = (event: SyntheticEvent) => {
  event.stopPropagation();
};

const renderEntityLink = (entityRef: Transaction['from_entity']) => (
  <Anchor
    size="sm"
    component={Link}
    to={`/profile/${entityRef.id}`}
    underline="hover"
    inherit
    onClick={stopRowClickPropagation}
    onKeyDown={stopRowClickPropagation}
  >
    {entityRef.name}
  </Anchor>
);

const truncateComment = (comment: string) => {
  if (comment.length <= COMMENT_PREVIEW_LENGTH) return comment;
  return `${comment.slice(0, COMMENT_PREVIEW_LENGTH)}...`;
};

export const transactionTableColumns: DataTableColumn<Transaction>[] = [
  { key: 'id', label: 'ID', render: (r) => <Text size="sm">{r.id}</Text> },
  {
    key: 'created_at',
    label: 'Date',
    headerStyle: { minWidth: 140, whiteSpace: 'nowrap' },
    cellStyle: { minWidth: 140, whiteSpace: 'nowrap' },
    render: (r) => <RelativeDate isoString={r.created_at} />,
  },
  {
    key: 'from_entity',
    label: 'From',
    render: (r) => (
      <Group gap={6} wrap="wrap">
        {renderEntityLink(r.from_entity)}
        {r.from_entity.tags?.length ? <TagList tags={r.from_entity.tags} /> : null}
      </Group>
    ),
  },
  {
    key: 'to_entity',
    label: 'To',
    render: (r) => (
      <Group gap={6} wrap="wrap">
        {renderEntityLink(r.to_entity)}
        {r.to_entity.tags?.length ? <TagList tags={r.to_entity.tags} /> : null}
      </Group>
    ),
  },
  {
    key: 'amount',
    label: 'Amount',
    render: (r) => <AmountCurrency amount={r.amount} currency={r.currency} />,
  },
  {
    key: 'treasury',
    label: 'Treasury',
    render: (r) => {
      const hasTreasury = r.from_treasury_id ?? r.to_treasury_id;
      if (!hasTreasury) return <Text size="sm">—</Text>;
      return (
        <Text size="sm">
          {r.from_treasury?.name ?? 'x'} → {r.to_treasury?.name ?? 'x'}
        </Text>
      );
    },
  },
  {
    key: 'tags',
    label: 'Tags',
    render: (r) => (r.tags.length ? <TagList tags={r.tags} /> : <Text size="sm">—</Text>),
  },
  {
    key: 'comment',
    label: 'Comment',
    cellStyle: { maxWidth: 260 },
    render: (r) => {
      const comment = r.comment?.trim();
      if (!comment) return <Text size="sm">—</Text>;

      const preview = truncateComment(comment);
      if (preview === comment) return <Text size="sm">{comment}</Text>;

      return (
        <Tooltip label={comment} multiline maw={360}>
          <Text size="sm">{preview}</Text>
        </Tooltip>
      );
    },
  },
  {
    key: 'invoice_id',
    label: 'Invoice',
    render: (r) => (r.invoice_id ? <Text size="sm">{r.invoice_id}</Text> : <Text size="sm">—</Text>),
  },
  {
    key: 'status',
    label: 'Status',
    render: (r) => (
      <Text size="sm" c={r.status === 'completed' ? 'green' : 'gray'}>
        {r.status}
      </Text>
    ),
  },
  {
    key: 'actor_entity',
    label: 'Actor',
    render: (r) => (
      <Group gap={6} wrap="wrap">
        {renderEntityLink(r.actor_entity)}
        {r.actor_entity.tags?.length ? <TagList tags={r.actor_entity.tags} /> : null}
      </Group>
    ),
  },
];
