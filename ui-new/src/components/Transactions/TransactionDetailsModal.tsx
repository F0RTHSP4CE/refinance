import { Anchor, Badge, Box, Button, Group, Modal, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { RelativeDate, TagList } from '@/components/ui';
import type { EntityRef, Transaction } from '@/types/api';
import { formatDateTime } from '@/utils/date';

type TransactionDetailsModalProps = {
  opened: boolean;
  transaction: Transaction | null;
  onClose: () => void;
};

const statusColor = (status: Transaction['status']) => (status === 'completed' ? 'teal' : 'gray');

const getTreasuryPath = (transaction: Transaction) => {
  const hasTreasury = transaction.from_treasury_id ?? transaction.to_treasury_id;
  if (!hasTreasury) return '—';
  const fromName = transaction.from_treasury?.name ?? '—';
  const toName = transaction.to_treasury?.name ?? '—';
  return `${fromName} -> ${toName}`;
};

const SectionCard = ({ title, children }: { title: string; children: ReactNode }) => (
  <Paper withBorder radius="md" p="md">
    <Stack gap="xs">
      <Text size="xs" c="dimmed" tt="uppercase">
        {title}
      </Text>
      {children}
    </Stack>
  </Paper>
);

const DetailItem = ({ label, children }: { label: string; children: ReactNode }) => (
  <Stack gap={4}>
    <Text size="xs" c="dimmed" tt="uppercase">
      {label}
    </Text>
    <Box>{children}</Box>
  </Stack>
);

const EntityInline = ({ entity }: { entity: EntityRef }) => (
  <Group gap={6} align="center" wrap="wrap">
    <Anchor
      size="sm"
      component={Link}
      to={`/profile/${entity.id}`}
      underline="hover"
      inherit
      aria-label={`Open ${entity.name} profile`}
    >
      {entity.name}
    </Anchor>
    {entity.tags?.length ? <TagList tags={entity.tags} /> : null}
  </Group>
);

export const TransactionDetailsModal = ({
  opened,
  transaction,
  onClose,
}: TransactionDetailsModalProps) => {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={transaction ? `Transaction #${transaction.id}` : 'Transaction'}
      centered
      size="lg"
      closeOnClickOutside
      closeOnEscape
    >
      {transaction ? (
        <Stack gap="sm">
          <Group justify="space-between" gap="xs" wrap="wrap">
            <Text size="xs" c="dimmed">
              Created <RelativeDate isoString={transaction.created_at} size="xs" />
            </Text>
            <Text size="xs" c="dimmed">
              {formatDateTime(transaction.created_at)}
            </Text>
          </Group>

          <SectionCard title="Amount">
            <Group justify="space-between" align="flex-start">
              <Box>
                <Text size="xl" fw={700}>
                  {transaction.amount} {transaction.currency.toUpperCase()}
                </Text>
              </Box>
              <Badge variant="light" color={statusColor(transaction.status)} tt="capitalize">
                {transaction.status}
              </Badge>
            </Group>
          </SectionCard>

          <SectionCard title="Participants">
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
              <DetailItem label="From">
                <EntityInline entity={transaction.from_entity} />
              </DetailItem>
              <DetailItem label="To">
                <EntityInline entity={transaction.to_entity} />
              </DetailItem>
              <DetailItem label="Author">
                <EntityInline entity={transaction.actor_entity} />
              </DetailItem>
            </SimpleGrid>
          </SectionCard>

          <SectionCard title="Context">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <DetailItem label="Treasury">
                <Text size="sm" style={{ wordBreak: 'break-word' }}>
                  {getTreasuryPath(transaction)}
                </Text>
              </DetailItem>
              <DetailItem label="Invoice">
                <Text size="sm">{transaction.invoice_id ?? '—'}</Text>
              </DetailItem>
              <DetailItem label="Transaction Tags">
                {transaction.tags.length ? <TagList tags={transaction.tags} showAll /> : <Text size="sm">—</Text>}
              </DetailItem>
            </SimpleGrid>
          </SectionCard>

          <SectionCard title="Comment">
            <Text
              size="sm"
              style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 180, overflowY: 'auto' }}
            >
              {transaction.comment || '—'}
            </Text>
          </SectionCard>

          <Group justify="flex-end" mt={4}>
            <Button variant="subtle" onClick={onClose}>
              Close
            </Button>
          </Group>
        </Stack>
      ) : null}
    </Modal>
  );
};
