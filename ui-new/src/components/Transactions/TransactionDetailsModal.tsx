import {
  Alert,
  Box,
  Button,
  Group,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';
import { completeTransaction, deleteTransaction, updateTransaction } from '@/api/transactions';
import {
  AppSelect,
  AppModal,
  AppModalFooter,
  DetailItem,
  DetailSectionCard,
  EntityInline,
  InlineMeta,
  ModalStepHeader,
  RelativeDate,
  StatusBadge,
  TagList,
} from '@/components/ui';
import { CURRENCIES } from '@/constants/entities';
import { useAuthStore } from '@/stores/auth';
import type { Transaction } from '@/types/api';
import { formatDateTime } from '@/utils/date';

type TransactionDetailsModalProps = {
  opened: boolean;
  transaction: Transaction | null;
  onClose: () => void;
  onUpdated?: (transaction: Transaction) => void;
  onDeleted?: (transactionId: number) => void;
};

const transactionDraftSchema = z.object({
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(CURRENCIES),
  comment: z.string().optional(),
});

type TransactionDraftFormValues = z.infer<typeof transactionDraftSchema>;

const getTreasuryPath = (transaction: Transaction) => {
  const hasTreasury = transaction.from_treasury_id ?? transaction.to_treasury_id;
  if (!hasTreasury) return '—';
  const fromName = transaction.from_treasury?.name ?? '—';
  const toName = transaction.to_treasury?.name ?? '—';
  return `${fromName} -> ${toName}`;
};

const getDefaultDraftValues = (transaction: Transaction | null): TransactionDraftFormValues => ({
  amount: transaction ? Number(transaction.amount) : 0,
  currency: (transaction?.currency.toUpperCase() as (typeof CURRENCIES)[number]) ?? 'GEL',
  comment: transaction?.comment ?? '',
});

export const TransactionDetailsModal = ({
  opened,
  transaction,
  onClose,
  onUpdated,
  onDeleted,
}: TransactionDetailsModalProps) => {
  const queryClient = useQueryClient();
  const viewerEntityId = useAuthStore((state) => state.actorEntity?.id ?? null);
  const [sheetMode, setSheetMode] = useState<'details' | 'edit'>('details');
  const [patchedTransaction, setPatchedTransaction] = useState<Transaction | null>(null);
  const activeTransaction =
    patchedTransaction && patchedTransaction.id === transaction?.id
      ? patchedTransaction
      : transaction;
  const isDraft = activeTransaction?.status === 'draft';
  const isSender = viewerEntityId != null && activeTransaction?.from_entity_id === viewerEntityId;
  const isRecipient =
    viewerEntityId != null && activeTransaction?.to_entity_id === viewerEntityId;
  const isActor = viewerEntityId != null && activeTransaction?.actor_entity_id === viewerEntityId;
  const canEditDraft = Boolean(isDraft && isSender);
  const canCompleteDraft = Boolean(isDraft && (isSender || isRecipient));
  const canDeleteDraft = Boolean(isDraft && (isSender || isRecipient || isActor));
  const deleteLabel = isRecipient && !isSender ? 'Decline request' : 'Delete';
  const completeLabel = isRecipient && !isSender ? 'Complete request' : 'Complete';

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TransactionDraftFormValues>({
    resolver: zodResolver(transactionDraftSchema),
    defaultValues: getDefaultDraftValues(activeTransaction),
  });

  useEffect(() => {
    reset(getDefaultDraftValues(activeTransaction));
  }, [activeTransaction, reset]);

  const invalidateRelatedQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['transactions'] }),
      queryClient.invalidateQueries({ queryKey: ['balances'] }),
      queryClient.invalidateQueries({ queryKey: ['invoices'] }),
      queryClient.invalidateQueries({ queryKey: ['pendingInvoices'] }),
      queryClient.invalidateQueries({ queryKey: ['fees'] }),
    ]);
  };

  const updateMutation = useMutation({
    mutationFn: async (values: TransactionDraftFormValues) => {
      if (!activeTransaction) {
        throw new Error('Transaction is missing.');
      }

      return updateTransaction(activeTransaction.id, {
        amount: values.amount,
        currency: values.currency,
        comment: values.comment?.trim() || undefined,
      });
    },
    onSuccess: async (updatedTransaction) => {
      await invalidateRelatedQueries();
      setPatchedTransaction(updatedTransaction);
      setSheetMode('details');
      onUpdated?.(updatedTransaction);
    },
  });

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (!activeTransaction) {
        throw new Error('Transaction is missing.');
      }
      return completeTransaction(activeTransaction.id);
    },
    onSuccess: async (updatedTransaction) => {
      await invalidateRelatedQueries();
      setPatchedTransaction(updatedTransaction);
      onUpdated?.(updatedTransaction);
    },
  });

  const handleClose = () => {
    setSheetMode('details');
    setPatchedTransaction(null);
    onClose();
  };

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!activeTransaction) {
        throw new Error('Transaction is missing.');
      }
      return deleteTransaction(activeTransaction.id);
    },
    onSuccess: async (transactionId) => {
      await invalidateRelatedQueries();
      onDeleted?.(transactionId);
      handleClose();
    },
  });

  const actionError =
    updateMutation.error?.message ||
    completeMutation.error?.message ||
    deleteMutation.error?.message;
  const footer = (
    sheetMode === 'edit' ? (
      <AppModalFooter
        secondary={
          <Button variant="subtle" onClick={() => setSheetMode('details')}>
            Back
          </Button>
        }
        primary={
          <Button
            type="submit"
            form="transaction-edit-form"
            variant="default"
            loading={updateMutation.isPending}
          >
            Save changes
          </Button>
        }
      />
    ) : (
      <AppModalFooter
        secondary={
          <Button variant="subtle" onClick={handleClose}>
            Close
          </Button>
        }
        primary={
          isDraft && (canDeleteDraft || canEditDraft || canCompleteDraft) ? (
            <Group gap="xs">
              {canDeleteDraft ? (
                <Button
                  color="red"
                  variant="light"
                  onClick={() => deleteMutation.mutate()}
                  loading={deleteMutation.isPending}
                >
                  {deleteLabel}
                </Button>
              ) : null}
              {canEditDraft ? (
                <Button variant="outline" onClick={() => setSheetMode('edit')}>
                  Edit
                </Button>
              ) : null}
              {canCompleteDraft ? (
                <Button
                  variant="default"
                  onClick={() => completeMutation.mutate()}
                  loading={completeMutation.isPending}
                >
                  {completeLabel}
                </Button>
              ) : null}
            </Group>
          ) : null
        }
      />
    )
  );

  return (
    <AppModal
      opened={opened}
      onClose={handleClose}
      title={
        sheetMode === 'edit'
          ? activeTransaction
            ? `Edit Draft #${activeTransaction.id}`
            : 'Edit draft'
          : activeTransaction
            ? `Transaction #${activeTransaction.id}`
            : 'Transaction'
      }
      variant={sheetMode === 'edit' ? 'form' : 'detail'}
      subtitle={
        sheetMode === 'edit'
          ? 'Only the amount, currency, and note can be changed in draft edit mode.'
          : 'Inspect the record, then edit or complete it if it is still a draft.'
      }
      footer={footer}
    >
      {activeTransaction ? (
        sheetMode === 'edit' ? (
          <form
            id="transaction-edit-form"
            onSubmit={(event) => void handleSubmit((values) => updateMutation.mutate(values))(event)}
          >
            <Stack gap="md">
              <ModalStepHeader
                eyebrow="Draft editor"
                title={`Draft #${activeTransaction.id}`}
                description="From, to, and actor stay fixed once the draft exists."
              />
              <Group grow align="start">
                <Controller
                  name="amount"
                  control={control}
                  render={({ field }) => (
                    <NumberInput
                      label="Amount"
                      min={0.01}
                      step={0.01}
                      decimalScale={2}
                      placeholder="0.00"
                      value={field.value}
                      onChange={(value) => field.onChange(typeof value === 'number' ? value : 0)}
                      error={errors.amount?.message}
                    />
                  )}
                />
              <Controller
                name="currency"
                control={control}
                render={({ field }) => (
                  <AppSelect
                    label="Currency"
                    data={CURRENCIES.map((currency) => ({ value: currency, label: currency }))}
                    value={field.value}
                      onChange={field.onChange}
                      error={errors.currency?.message}
                      allowDeselect={false}
                    />
                  )}
                />
              </Group>

              <Controller
                name="comment"
                control={control}
                render={({ field }) => (
                  <TextInput
                    label="Comment"
                    placeholder="Optional note"
                    value={field.value || ''}
                    onChange={field.onChange}
                  />
                )}
              />

              <Text size="sm" c="dimmed">
                From, to, and actor cannot be changed in draft edit mode.
              </Text>

              {updateMutation.isError ? (
                <Alert color="red" title="Could not update draft">
                  {updateMutation.error.message}
                </Alert>
              ) : null}
            </Stack>
          </form>
        ) : (
          <Stack gap="sm">
            <ModalStepHeader
              eyebrow="Transaction details"
              title={`#${activeTransaction.id}`}
              description={`Created ${formatDateTime(activeTransaction.created_at)}`}
            />
            <InlineMeta
              items={[
                <>
                  Created <RelativeDate isoString={activeTransaction.created_at} size="xs" />
                </>,
                <>Author: {activeTransaction.actor_entity.name}</>,
              ]}
            />

            <DetailSectionCard title="Amount">
              <Group justify="space-between" align="flex-start">
                <Box>
                  <Text size="xl" fw={700}>
                    {activeTransaction.amount} {activeTransaction.currency.toUpperCase()}
                  </Text>
                </Box>
                <StatusBadge tone={activeTransaction.status === 'completed' ? 'success' : 'draft'}>
                  {activeTransaction.status}
                </StatusBadge>
              </Group>
            </DetailSectionCard>

            <DetailSectionCard title="Participants">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailItem label="From">
                  <EntityInline entity={activeTransaction.from_entity} />
                </DetailItem>
                <DetailItem label="To">
                  <EntityInline entity={activeTransaction.to_entity} />
                </DetailItem>
              </SimpleGrid>
            </DetailSectionCard>

            <DetailSectionCard title="Context">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailItem label="Treasury">
                  <Text size="sm" style={{ wordBreak: 'break-word' }}>
                    {getTreasuryPath(activeTransaction)}
                  </Text>
                </DetailItem>
                <DetailItem label="Invoice">
                  <Text size="sm">{activeTransaction.invoice_id ?? '—'}</Text>
                </DetailItem>
                <DetailItem label="Transaction labels">
                  {activeTransaction.tags.length ? (
                    <TagList tags={activeTransaction.tags} showAll />
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
                {activeTransaction.comment || '—'}
              </Text>
            </DetailSectionCard>

            {isDraft ? (
              isRecipient && !isSender ? (
                <Alert color="blue" title="Incoming request">
                  This draft is addressed to you. You can complete the request or decline it from
                  this sheet.
                </Alert>
              ) : isSender ? (
                <Alert color="blue" title="Draft actions">
                  You can still edit the amount, currency, or comment here, then complete or delete
                  the draft without leaving this sheet.
                </Alert>
              ) : isActor ? (
                <Alert color="gray" title="Creator view">
                  You created this draft, but only the involved entities can complete it. You can
                  still remove it if it should not stay open.
                </Alert>
              ) : null
            ) : null}

            {actionError ? (
              <Alert color="red" title="Action failed">
                {actionError}
              </Alert>
            ) : null}
          </Stack>
        )
      ) : null}
    </AppModal>
  );
};
