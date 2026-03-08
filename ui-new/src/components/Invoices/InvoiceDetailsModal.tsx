import { Button, Group, Modal, Skeleton, SimpleGrid, Stack, Text } from '@mantine/core';
import {
  DetailItem,
  DetailSectionCard,
  EntityInline,
  RelativeDate,
  StatusBadge,
  TagList,
} from '@/components/ui';
import type { Invoice } from '@/types/api';
import { formatDateTime } from '@/utils/date';

type InvoiceDetailsModalProps = {
  opened: boolean;
  invoice: Invoice | null;
  loading?: boolean;
  onClose: () => void;
  onEdit?: (invoice: Invoice) => void;
  onPay?: (invoice: Invoice) => void;
  onDelete?: (invoice: Invoice) => void;
};

const formatBillingPeriod = (period?: string | null) => {
  if (!period) return '—';
  return new Date(period).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatAmountOptions = (invoice: Invoice) =>
  invoice.amounts.map((item) => `${item.amount} ${item.currency.toUpperCase()}`).join(' or ');

const getInvoiceTone = (status: Invoice['status']) => (status === 'paid' ? 'positive' : 'neutral');

export const InvoiceDetailsModal = ({
  opened,
  invoice,
  loading = false,
  onClose,
  onEdit,
  onPay,
  onDelete,
}: InvoiceDetailsModalProps) => {
  const isPending = invoice?.status === 'pending';

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={invoice ? `Invoice #${invoice.id}` : 'Invoice'}
      centered
      size="lg"
      closeOnClickOutside
      closeOnEscape
    >
      {invoice ? (
        <Stack gap="sm">
          <Group justify="space-between" gap="xs" wrap="wrap">
            <Group gap="xs" wrap="wrap">
              <Text size="xs" c="dimmed">
                Created <RelativeDate isoString={invoice.created_at} size="xs" />
              </Text>
              <Text size="xs" c="dimmed">
                {formatDateTime(invoice.created_at)}
              </Text>
            </Group>
            <Group gap={6} wrap="wrap">
              <Text size="xs" c="dimmed" tt="uppercase">
                Author
              </Text>
              <EntityInline entity={invoice.actor_entity} size="xs" tagMode="expanded" />
            </Group>
          </Group>

          <DetailSectionCard title="Amount">
            <Group justify="space-between" align="flex-start">
              <Text size="xl" fw={700}>
                {formatAmountOptions(invoice)}
              </Text>
              <StatusBadge tone={getInvoiceTone(invoice.status)}>{invoice.status}</StatusBadge>
            </Group>
          </DetailSectionCard>

          <DetailSectionCard title="Participants">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <DetailItem label="From">
                <EntityInline entity={invoice.from_entity} tagMode="expanded" />
              </DetailItem>
              <DetailItem label="To">
                <EntityInline entity={invoice.to_entity} tagMode="expanded" />
              </DetailItem>
            </SimpleGrid>
          </DetailSectionCard>

          <DetailSectionCard title="Context">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <DetailItem label="Billing period">
                <Text size="sm">{formatBillingPeriod(invoice.billing_period)}</Text>
              </DetailItem>
              <DetailItem label="Transaction">
                <Text size="sm">{invoice.transaction_id ?? '—'}</Text>
              </DetailItem>
              <DetailItem label="Invoice Tags">
                {invoice.tags.length ? (
                  <TagList tags={invoice.tags} mode="expanded" />
                ) : (
                  <Text size="sm">—</Text>
                )}
              </DetailItem>
            </SimpleGrid>
          </DetailSectionCard>

          <DetailSectionCard title="Comment">
            <Text
              size="sm"
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: 180,
                overflowY: 'auto',
              }}
            >
              {invoice.comment || '—'}
            </Text>
          </DetailSectionCard>

          {!isPending ? (
            <Text size="sm" c="dimmed">
              This invoice can no longer be changed.
            </Text>
          ) : null}

          <Group justify="space-between" mt={4}>
            <Group gap="xs">
              {isPending && onPay ? (
                <Button variant="default" onClick={() => onPay(invoice)}>
                  Pay
                </Button>
              ) : null}
              {isPending && onEdit ? (
                <Button variant="outline" onClick={() => onEdit(invoice)}>
                  Edit
                </Button>
              ) : null}
              {isPending && !invoice.transaction_id && onDelete ? (
                <Button color="red" variant="outline" onClick={() => onDelete(invoice)}>
                  Delete
                </Button>
              ) : null}
            </Group>
            <Button variant="subtle" onClick={onClose}>
              Close
            </Button>
          </Group>
        </Stack>
      ) : loading ? (
        <Stack gap="sm">
          <Group justify="space-between" gap="xs" wrap="wrap">
            <Skeleton height={16} width={180} radius="sm" />
            <Skeleton height={16} width={160} radius="sm" />
          </Group>

          <DetailSectionCard title="Amount">
            <Group justify="space-between" align="flex-start">
              <Skeleton height={34} width="55%" radius="sm" />
              <Skeleton height={32} width={90} radius="sm" />
            </Group>
          </DetailSectionCard>

          <DetailSectionCard title="Participants">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <Skeleton height={64} radius="sm" />
              <Skeleton height={64} radius="sm" />
            </SimpleGrid>
          </DetailSectionCard>

          <DetailSectionCard title="Context">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <Skeleton height={52} radius="sm" />
              <Skeleton height={52} radius="sm" />
              <Skeleton height={52} radius="sm" />
            </SimpleGrid>
          </DetailSectionCard>

          <DetailSectionCard title="Comment">
            <Skeleton height={84} radius="sm" />
          </DetailSectionCard>
        </Stack>
      ) : null}
    </Modal>
  );
};
