import { Button, Card, Group, Modal, Stack, Text, UnstyledButton } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getTransactions } from '@/api/transactions';
import { RelativeDate, StatusBadge, TagList } from '@/components/ui';
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
  const [opened, { open, close }] = useDisclosure(false);
  const [selectedDraft, setSelectedDraft] = useState<Transaction | null>(null);

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

  const openDraft = (draft: Transaction) => {
    setSelectedDraft(draft);
    open();
  };

  return (
    <>
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Text size="lg" fw={700}>
              Drafts
            </Text>
            {draftCount > 0 && (
              <StatusBadge size="lg" tone="neutral">
                {draftCount}
              </StatusBadge>
            )}
          </Group>

          {drafts.length === 0 ? (
            <Text size="sm" c="dimmed">
              No draft transactions.
            </Text>
          ) : (
            <Stack gap="xs">
              {drafts.map((draft) => (
                <UnstyledButton
                  key={draft.id}
                  onClick={() => openDraft(draft)}
                  style={{
                    width: '100%',
                    border: '1px solid var(--mantine-color-default-border)',
                    borderRadius: 'var(--mantine-radius-sm)',
                    padding: '8px',
                    textAlign: 'left',
                  }}
                >
                  <Group justify="space-between" align="start">
                    <Stack gap={2}>
                      <Text size="sm">{draftLabel(draft, actorEntity?.id ?? 0)}</Text>
                      <RelativeDate isoString={draft.created_at} size="xs" />
                    </Stack>
                    <Group gap="xs" align="center">
                      <Text size="sm" fw={700}>
                        {formatAmount(draft.amount, draft.currency)}
                      </Text>
                      <StatusBadge tone="neutral" size="sm">
                        draft
                      </StatusBadge>
                    </Group>
                  </Group>
                </UnstyledButton>
              ))}
            </Stack>
          )}
        </Stack>
      </Card>

      <Modal
        opened={opened}
        onClose={close}
        title={selectedDraft ? `Draft Transaction #${selectedDraft.id}` : 'Draft Transaction'}
        centered
      >
        {selectedDraft ? (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Created
              </Text>
              <RelativeDate isoString={selectedDraft.created_at} />
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                From
              </Text>
              <Text size="sm">{selectedDraft.from_entity.name}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                To
              </Text>
              <Text size="sm">{selectedDraft.to_entity.name}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Amount
              </Text>
              <Text size="sm" fw={700}>
                {formatAmount(selectedDraft.amount, selectedDraft.currency)}
              </Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Status
              </Text>
              <StatusBadge tone="neutral" size="sm">
                {selectedDraft.status}
              </StatusBadge>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Actor
              </Text>
              <Text size="sm">{selectedDraft.actor_entity.name}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Treasury
              </Text>
              <Text size="sm">
                {selectedDraft.from_treasury?.name ?? 'x'} →{' '}
                {selectedDraft.to_treasury?.name ?? 'x'}
              </Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Invoice
              </Text>
              <Text size="sm">{selectedDraft.invoice_id ?? '—'}</Text>
            </Group>
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                Tags
              </Text>
              {selectedDraft.tags.length ? (
                <TagList tags={selectedDraft.tags} />
              ) : (
                <Text size="sm">—</Text>
              )}
            </Stack>
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                Comment
              </Text>
              <Text size="sm">{selectedDraft.comment || '—'}</Text>
            </Stack>
            {actorEntity && (
              <Button
                component={Link}
                to={`/profile/${actorEntity.id}?tab=profile`}
                variant="light"
                size="xs"
                onClick={close}
              >
                Open Profile Transactions
              </Button>
            )}
          </Stack>
        ) : null}
      </Modal>
    </>
  );
};
