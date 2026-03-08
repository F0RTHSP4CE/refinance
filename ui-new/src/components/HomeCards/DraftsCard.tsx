import { Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { getTransactions } from '@/api/transactions';
import {
  EmptyState,
  RelativeDate,
  SectionCard,
  StatusBadge,
} from '@/components/ui';
import { TransactionDetailsModal, useTransactionDetailsModal } from '@/components/Transactions';
import { useAuthStore } from '@/stores/auth';
import type { Transaction } from '@/types/api';

const LIMIT = 10;

const formatAmount = (amount: string, currency: string) =>
  `${parseFloat(amount).toFixed(2)} ${currency.toUpperCase()}`;

const draftLabel = (transaction: Transaction, actorEntityId: number) => {
  const isSender = transaction.from_entity_id === actorEntityId;
  const isRecipient = transaction.to_entity_id === actorEntityId;
  const isActor = transaction.actor_entity_id === actorEntityId;

  if (isRecipient && !isSender) return `Incoming request from ${transaction.from_entity.name}`;
  if (isSender && !isRecipient) return `Incomplete transaction to ${transaction.to_entity.name}`;
  if (isActor && !isSender && !isRecipient) {
    return `Created by you: ${transaction.from_entity.name} -> ${transaction.to_entity.name}`;
  }
  return `Draft transaction ${transaction.from_entity.name} -> ${transaction.to_entity.name}`;
};

export const DraftsCard = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const { opened, selectedTransaction, openTransaction, closeTransaction } =
    useTransactionDetailsModal();

  const { data: draftsResponse } = useQuery({
    queryKey: ['draftTransactionsCard', actorEntity?.id, LIMIT],
    queryFn: ({ signal }) =>
      getTransactions({
        entity_id: actorEntity!.id,
        status: 'draft',
        limit: LIMIT,
        signal,
      }),
    enabled: actorEntity !== null,
  });

  const drafts = draftsResponse?.items ?? [];
  const draftCount = draftsResponse?.total ?? 0;

  return (
    <>
      <SectionCard
        title="Draft activity"
        description="Finish outgoing drafts and respond to incoming requests before they go stale."
        action={
          draftCount > 0 ? (
            <StatusBadge size="lg" tone="draft">
              {draftCount}
            </StatusBadge>
          ) : null
        }
      >
        <Stack gap="md">
          {drafts.length === 0 ? (
            <EmptyState
              compact
              title="No draft transactions"
              description="New requests and unfinished transfers will land here."
            />
          ) : (
            <Stack gap="xs">
              {drafts.map((draft) => (
                <UnstyledButton
                  key={draft.id}
                  onClick={() => openTransaction(draft)}
                  style={{
                    width: '100%',
                    border: '1px solid var(--app-border-subtle)',
                    borderRadius: '0.9rem',
                    padding: '0.7rem 0.8rem',
                    background: 'rgba(255, 255, 255, 0.025)',
                    textAlign: 'left',
                  }}
                >
                  <Group justify="space-between" align="start">
                    <Stack gap={2}>
                      <Text size="sm" fw={600}>
                        {draftLabel(draft, actorEntity?.id ?? 0)}
                      </Text>
                      <RelativeDate isoString={draft.created_at} size="xs" />
                    </Stack>
                    <Group gap="xs" align="center">
                      <Text size="sm" fw={700}>
                        {formatAmount(draft.amount, draft.currency)}
                      </Text>
                      <StatusBadge tone="draft" size="sm">
                        draft
                      </StatusBadge>
                    </Group>
                  </Group>
                </UnstyledButton>
              ))}
            </Stack>
          )}
        </Stack>
      </SectionCard>

      <TransactionDetailsModal
        opened={opened}
        transaction={selectedTransaction}
        onClose={closeTransaction}
      />
    </>
  );
};
