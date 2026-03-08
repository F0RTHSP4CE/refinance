import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { deleteSplit, getSplit, performSplit, removeSplitParticipant } from '@/api/splits';
import { TransactionDetailsModal, useTransactionDetailsModal } from '@/components/Transactions';
import {
  DataTable,
  DetailItem,
  DetailSectionCard,
  EntityInline,
  RelativeDate,
  StatusBadge,
  TagList,
  type DataTableColumn,
} from '@/components/ui';
import type { Transaction } from '@/types/api';
import { SplitEditorModal } from './SplitEditorModal';
import { SplitParticipantModal } from './SplitParticipantModal';
import { SplitProgressBar } from './SplitProgressBar';
import {
  formatSplitMoney,
  getDisplayedCollectedAmount,
  getSplitDisplayName,
  getSplitParticipantColor,
  getSplitParticipantShare,
} from './splitUtils';

type SplitDetailsModalProps = {
  opened: boolean;
  splitId: number | null;
  onClose: () => void;
  onDeleted?: (splitId: number) => void;
};

const formatDateTime = (iso?: string | null) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

export const SplitDetailsModal = ({
  opened,
  splitId,
  onClose,
  onDeleted,
}: SplitDetailsModalProps) => {
  const queryClient = useQueryClient();
  const [editorOpened, setEditorOpened] = useState(false);
  const [participantModalOpened, setParticipantModalOpened] = useState(false);
  const [performConfirmOpened, setPerformConfirmOpened] = useState(false);
  const [deleteConfirmOpened, setDeleteConfirmOpened] = useState(false);
  const {
    opened: transactionOpened,
    selectedTransaction,
    openTransaction,
    closeTransaction,
  } = useTransactionDetailsModal();

  const splitQuery = useQuery({
    queryKey: ['split', splitId],
    queryFn: ({ signal }) => getSplit(splitId!, signal),
    enabled: opened && splitId != null,
  });

  const split = splitQuery.data ?? null;

  const invalidateSplitQueries = async (id: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['splits'] }),
      queryClient.invalidateQueries({ queryKey: ['split', id] }),
      queryClient.invalidateQueries({ queryKey: ['transactions'] }),
      queryClient.invalidateQueries({ queryKey: ['balances'] }),
    ]);
  };

  const performMutation = useMutation({
    mutationFn: async () => {
      if (splitId == null) {
        throw new Error('Split is missing.');
      }
      return performSplit(splitId);
    },
    onSuccess: async (updatedSplit) => {
      await invalidateSplitQueries(updatedSplit.id);
      queryClient.setQueryData(['split', updatedSplit.id], updatedSplit);
      setPerformConfirmOpened(false);
    },
  });

  const removeParticipantMutation = useMutation({
    mutationFn: async (entityId: number) => {
      if (splitId == null) {
        throw new Error('Split is missing.');
      }
      return removeSplitParticipant(splitId, entityId);
    },
    onSuccess: async (updatedSplit) => {
      await invalidateSplitQueries(updatedSplit.id);
      queryClient.setQueryData(['split', updatedSplit.id], updatedSplit);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (splitId == null) {
        throw new Error('Split is missing.');
      }
      return deleteSplit(splitId);
    },
    onSuccess: async (deletedId) => {
      await invalidateSplitQueries(deletedId);
      setDeleteConfirmOpened(false);
      onDeleted?.(deletedId);
      onClose();
    },
  });

  const mutationError =
    performMutation.error?.message ||
    removeParticipantMutation.error?.message ||
    deleteMutation.error?.message;

  const transactionColumns: DataTableColumn<Transaction>[] = [
    {
      key: 'id',
      label: 'Transaction',
      render: (transaction) => <Text size="sm">#{transaction.id}</Text>,
    },
    {
      key: 'from_entity',
      label: 'From',
      render: (transaction) => <Text size="sm">{transaction.from_entity.name}</Text>,
    },
    {
      key: 'to_entity',
      label: 'To',
      render: (transaction) => <Text size="sm">{transaction.to_entity.name}</Text>,
    },
    {
      key: 'amount',
      label: 'Amount',
      render: (transaction) => (
        <Text size="sm">
          {formatSplitMoney(transaction.amount)} {transaction.currency.toUpperCase()}
        </Text>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (transaction) => <Text size="sm">{formatDateTime(transaction.created_at)}</Text>,
    },
  ];

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        title={split ? getSplitDisplayName(split) : 'Split'}
        centered
        size="xl"
      >
        {split ? (
          <Stack gap="sm">
            <Group justify="space-between" gap="xs" wrap="wrap">
              <Group gap="xs" wrap="wrap">
                <Text size="xs" c="dimmed">
                  #{split.id}
                </Text>
                <StatusBadge tone={split.performed ? 'positive' : 'neutral'}>
                  {split.performed ? 'done' : 'active'}
                </StatusBadge>
              </Group>
              <Group gap="xs" wrap="wrap">
                <Text size="xs" c="dimmed">
                  Created <RelativeDate isoString={split.created_at} size="xs" />
                </Text>
                <Text size="xs" c="dimmed">
                  {formatDateTime(split.created_at)}
                </Text>
              </Group>
            </Group>

            <DetailSectionCard title="Amount">
              <Stack gap="md">
                <Group justify="space-between" align="flex-start" gap="sm" wrap="wrap">
                  <Stack gap={4}>
                    <Text size="xl" fw={700}>
                      {getDisplayedCollectedAmount(split)} / {formatSplitMoney(split.amount)}{' '}
                      {split.currency.toUpperCase()}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {split.participants.length} participant
                      {split.participants.length === 1 ? '' : 's'} currently included
                    </Text>
                  </Stack>
                  <StatusBadge tone={split.performed ? 'positive' : 'neutral'}>
                    {split.performed ? 'performed' : 'collecting'}
                  </StatusBadge>
                </Group>
                <SplitProgressBar split={split} height={16} showLegend />
              </Stack>
            </DetailSectionCard>

            <DetailSectionCard title="Participants">
              {split.participants.length ? (
                <Stack gap="sm">
                  {split.participants.map((participant) => (
                    <Paper key={participant.entity.id} withBorder radius="md" p="sm">
                      <Group justify="space-between" align="flex-start" gap="sm" wrap="nowrap">
                        <Group align="flex-start" gap="sm" wrap="nowrap">
                          <div
                            style={{
                              width: 12,
                              height: 12,
                              marginTop: 5,
                              borderRadius: 999,
                              background: getSplitParticipantColor(participant.entity.id),
                              flexShrink: 0,
                            }}
                          />
                          <Stack gap={4}>
                            <Text fw={600}>{participant.entity.name}</Text>
                            {participant.entity.tags.length ? (
                              <TagList tags={participant.entity.tags} mode="compact" />
                            ) : null}
                          </Stack>
                        </Group>

                        <Group gap="xs" wrap="nowrap">
                          {participant.fixed_amount ? (
                            <StatusBadge tone="neutral">fixed</StatusBadge>
                          ) : null}
                          <Text fw={700} size="sm">
                            {formatSplitMoney(getSplitParticipantShare(participant, split))}{' '}
                            {split.currency.toUpperCase()}
                          </Text>
                          {!split.performed ? (
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              aria-label={`Remove ${participant.entity.name}`}
                              onClick={() =>
                                removeParticipantMutation.mutate(participant.entity.id)
                              }
                              loading={removeParticipantMutation.isPending}
                            >
                              <IconX size={16} />
                            </ActionIcon>
                          ) : null}
                        </Group>
                      </Group>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  No participants yet.
                </Text>
              )}
            </DetailSectionCard>

            <DetailSectionCard title="Context">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailItem label="Recipient">
                  <EntityInline entity={split.recipient_entity} tagMode="expanded" />
                </DetailItem>
                <DetailItem label="Author">
                  <EntityInline entity={split.actor_entity} tagMode="expanded" />
                </DetailItem>
                <DetailItem label="Modified">
                  <Text size="sm">{formatDateTime(split.modified_at)}</Text>
                </DetailItem>
                <DetailItem label="Tags">
                  {split.tags.length ? (
                    <TagList tags={split.tags} mode="expanded" />
                  ) : (
                    <Text size="sm">—</Text>
                  )}
                </DetailItem>
              </SimpleGrid>
            </DetailSectionCard>

            <DetailSectionCard title="Actions">
              {!split.performed ? (
                <Group gap="xs" wrap="wrap">
                  <Button variant="default" onClick={() => setParticipantModalOpened(true)}>
                    Add participant
                  </Button>
                  <Button variant="default" onClick={() => setPerformConfirmOpened(true)}>
                    Perform
                  </Button>
                  <Button variant="outline" onClick={() => setEditorOpened(true)}>
                    Edit
                  </Button>
                  <Button
                    color="red"
                    variant="outline"
                    onClick={() => setDeleteConfirmOpened(true)}
                  >
                    Delete
                  </Button>
                </Group>
              ) : (
                <Text size="sm" c="dimmed">
                  This split has already been performed. You can still inspect its transactions
                  below.
                </Text>
              )}
            </DetailSectionCard>

            <DetailSectionCard title="Performed transactions">
              {split.performed ? (
                <DataTable
                  columns={transactionColumns}
                  data={split.performed_transactions}
                  emptyMessage="No transactions created."
                  onRowClick={openTransaction}
                  getRowAriaLabel={(transaction) => `Open transaction #${transaction.id}`}
                />
              ) : (
                <Text size="sm" c="dimmed">
                  Transactions will appear here after the split is performed.
                </Text>
              )}
            </DetailSectionCard>

            {mutationError ? (
              <Alert color="red" title="Could not update split">
                {mutationError}
              </Alert>
            ) : null}
          </Stack>
        ) : splitQuery.isLoading ? (
          <Text c="dimmed">Loading split...</Text>
        ) : (
          <Text c="dimmed">Split not found.</Text>
        )}
      </Modal>

      <SplitEditorModal
        opened={editorOpened}
        split={split}
        onClose={() => setEditorOpened(false)}
        onSaved={(updatedSplit) => {
          queryClient.setQueryData(['split', updatedSplit.id], updatedSplit);
          void invalidateSplitQueries(updatedSplit.id);
        }}
      />

      <SplitParticipantModal
        opened={participantModalOpened}
        splitId={splitId}
        mode="add"
        onClose={() => setParticipantModalOpened(false)}
        onSaved={(updatedSplit) => {
          queryClient.setQueryData(['split', updatedSplit.id], updatedSplit);
          void invalidateSplitQueries(updatedSplit.id);
        }}
      />

      <Modal
        opened={performConfirmOpened}
        onClose={() => setPerformConfirmOpened(false)}
        title={split ? `Perform ${getSplitDisplayName(split)}?` : 'Perform split?'}
        centered
      >
        <Stack gap="md">
          <Text>
            This will create completed transactions for each participant and mark the split as done.
          </Text>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setPerformConfirmOpened(false)}>
              Cancel
            </Button>
            <Button
              variant="default"
              onClick={() => performMutation.mutate()}
              loading={performMutation.isPending}
            >
              Perform
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={deleteConfirmOpened}
        onClose={() => setDeleteConfirmOpened(false)}
        title={split ? `Delete ${getSplitDisplayName(split)}?` : 'Delete split?'}
        centered
      >
        <Stack gap="md">
          <Text>This action removes the split permanently.</Text>
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setDeleteConfirmOpened(false)}>
              Cancel
            </Button>
            <Button
              color="red"
              variant="light"
              onClick={() => deleteMutation.mutate()}
              loading={deleteMutation.isPending}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <TransactionDetailsModal
        opened={transactionOpened}
        transaction={selectedTransaction}
        onClose={closeTransaction}
      />
    </>
  );
};
