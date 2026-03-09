import { ActionIcon, Alert, Button, Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { deleteSplit, getSplit, performSplit, removeSplitParticipant } from '@/api/splits';
import { TransactionDetailsModal, useTransactionDetailsModal } from '@/components/Transactions';
import {
  AppModal,
  AppModalFooter,
  DataTable,
  DetailItem,
  DetailSectionCard,
  EntityInline,
  ErrorState,
  InlineMeta,
  LoadingState,
  ModalStepHeader,
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
  const [sheetStep, setSheetStep] = useState<'details' | 'perform' | 'delete'>('details');
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
      setSheetStep('details');
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
      setSheetStep('details');
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

  const handleClose = () => {
    setSheetStep('details');
    onClose();
  };

  const footer =
    sheetStep === 'perform' ? (
      <AppModalFooter
        secondary={
          <Button variant="subtle" onClick={() => setSheetStep('details')}>
            Back
          </Button>
        }
        primary={
          <Button
            variant="default"
            onClick={() => performMutation.mutate()}
            loading={performMutation.isPending}
          >
            Perform split
          </Button>
        }
      />
    ) : sheetStep === 'delete' ? (
      <AppModalFooter
        secondary={
          <Button variant="subtle" onClick={() => setSheetStep('details')}>
            Back
          </Button>
        }
        primary={
          <Button
            color="red"
            variant="light"
            onClick={() => deleteMutation.mutate()}
            loading={deleteMutation.isPending}
          >
            Delete split
          </Button>
        }
      />
    ) : split && !split.performed ? (
      <AppModalFooter
        secondary={
          <Button variant="subtle" onClick={handleClose}>
            Close
          </Button>
        }
        primary={
          <Group gap="xs">
            <Button color="red" variant="subtle" onClick={() => setSheetStep('delete')}>
              Delete
            </Button>
            <Button variant="subtle" onClick={() => setEditorOpened(true)}>
              Edit
            </Button>
            <Button variant="outline" onClick={() => setParticipantModalOpened(true)}>
              Add participant
            </Button>
            <Button variant="default" onClick={() => setSheetStep('perform')}>
              Perform
            </Button>
          </Group>
        }
      />
    ) : (
      <AppModalFooter primary={<Button onClick={handleClose}>Close</Button>} />
    );

  return (
    <>
      <AppModal
        opened={opened}
        onClose={handleClose}
        title={
          sheetStep === 'perform'
            ? split
              ? `Perform ${getSplitDisplayName(split)}`
              : 'Perform split'
            : sheetStep === 'delete'
              ? split
                ? `Delete ${getSplitDisplayName(split)}`
                : 'Delete split'
              : split
                ? getSplitDisplayName(split)
                : 'Split'
        }
        variant="detail"
        subtitle={
          sheetStep === 'perform'
            ? 'Confirm this run to create the resulting completed transactions for every participant.'
            : sheetStep === 'delete'
              ? 'This removes the split definition and its participant setup.'
              : 'Inspect participants, progress, and follow-up actions from the same right-side flow.'
        }
        footer={footer}
      >
        {split ? sheetStep === 'perform' ? (
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Perform split"
              title={getSplitDisplayName(split)}
              description="This locks in the participant list and creates the completed transactions for every share."
            />
            <Alert color="blue" title="What happens next">
              Performing this split creates completed transactions for each participant share and
              marks the run as done.
            </Alert>
            <DetailSectionCard title="Ready to perform">
              <Stack gap="sm">
                <Text size="sm">
                  Recipient: <strong>{split.recipient_entity.name}</strong>
                </Text>
                <Text size="sm">
                  Participants: <strong>{split.participants.length}</strong>
                </Text>
                <Text size="sm">
                  Total amount:{' '}
                  <strong>
                    {formatSplitMoney(split.amount)} {split.currency.toUpperCase()}
                  </strong>
                </Text>
              </Stack>
            </DetailSectionCard>
            {mutationError ? (
              <Alert color="red" title="Could not update split">
                {mutationError}
              </Alert>
            ) : null}
          </Stack>
        ) : sheetStep === 'delete' ? (
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Delete split"
              title={getSplitDisplayName(split)}
              description="Remove this split run and its participant setup."
            />
            <Alert color="red" title="Permanent action">
              Deleting this split removes the setup permanently. Existing performed transactions are
              not recreated later.
            </Alert>
            {mutationError ? (
              <Alert color="red" title="Could not delete split">
                {mutationError}
              </Alert>
            ) : null}
          </Stack>
        ) : (
          <Stack gap="sm">
            <ModalStepHeader
              eyebrow="Split details"
              title={getSplitDisplayName(split)}
              description={`Created ${formatDateTime(split.created_at)}`}
            />
            <InlineMeta
              items={[
                `#${split.id}`,
                <StatusBadge tone={split.performed ? 'success' : 'info'}>
                  {split.performed ? 'done' : 'active'}
                </StatusBadge>,
                <>
                  Created <RelativeDate isoString={split.created_at} size="xs" />
                </>,
              ]}
            />

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
                  <StatusBadge tone={split.performed ? 'success' : 'info'}>
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
                            <StatusBadge tone="warning">fixed</StatusBadge>
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
          <LoadingState cards={1} lines={3} />
        ) : (
          <ErrorState
            compact
            title="Split run not found"
            description="This split run could not be loaded or no longer exists."
          />
        )}
      </AppModal>

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

      <TransactionDetailsModal
        opened={transactionOpened}
        transaction={selectedTransaction}
        onClose={closeTransaction}
      />
    </>
  );
};
