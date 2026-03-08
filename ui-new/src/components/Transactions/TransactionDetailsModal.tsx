import {
  Alert,
  Box,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
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
  DetailItem,
  DetailSectionCard,
  EntityInline,
  RelativeDate,
  StatusBadge,
  TagList,
} from '@/components/ui';
import { CURRENCIES } from '@/constants/entities';
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
  const [editingOpened, setEditingOpened] = useState(false);
  const [patchedTransaction, setPatchedTransaction] = useState<Transaction | null>(null);
  const activeTransaction =
    patchedTransaction && patchedTransaction.id === transaction?.id
      ? patchedTransaction
      : transaction;
  const isDraft = activeTransaction?.status === 'draft';

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
      setEditingOpened(false);
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
    setEditingOpened(false);
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

  return (
    <>
      <Modal
        opened={opened}
        onClose={handleClose}
        title={activeTransaction ? `Transaction #${activeTransaction.id}` : 'Transaction'}
        centered
        size="lg"
        closeOnClickOutside
        closeOnEscape
      >
        {activeTransaction ? (
          <Stack gap="sm">
            <Group justify="space-between" gap="xs" wrap="wrap">
              <Group gap="xs" wrap="wrap">
                <Text size="xs" c="dimmed">
                  Created <RelativeDate isoString={activeTransaction.created_at} size="xs" />
                </Text>
                <Text size="xs" c="dimmed">
                  {formatDateTime(activeTransaction.created_at)}
                </Text>
              </Group>
              <Group gap={6} wrap="wrap">
                <Text size="xs" c="dimmed" tt="uppercase">
                  Author
                </Text>
                <EntityInline entity={activeTransaction.actor_entity} size="xs" />
              </Group>
            </Group>

            <DetailSectionCard title="Amount">
              <Group justify="space-between" align="flex-start">
                <Box>
                  <Text size="xl" fw={700}>
                    {activeTransaction.amount} {activeTransaction.currency.toUpperCase()}
                  </Text>
                </Box>
                <StatusBadge
                  tone={activeTransaction.status === 'completed' ? 'positive' : 'neutral'}
                >
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
                <DetailItem label="Transaction Tags">
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
              <Alert color="blue" title="Draft actions">
                You can still edit the amount, currency, or comment, then complete or delete this
                draft. Parties stay fixed after creation.
              </Alert>
            ) : null}

            {actionError ? (
              <Alert color="red" title="Action failed">
                {actionError}
              </Alert>
            ) : null}

            <Group justify="space-between" mt={4}>
              <Group gap="xs">
                {isDraft ? (
                  <>
                    <Button variant="default" onClick={() => setEditingOpened(true)}>
                      Edit
                    </Button>
                    <Button
                      variant="default"
                      onClick={() => completeMutation.mutate()}
                      loading={completeMutation.isPending}
                    >
                      Complete
                    </Button>
                    <Button
                      color="red"
                      variant="light"
                      onClick={() => deleteMutation.mutate()}
                      loading={deleteMutation.isPending}
                    >
                      Delete
                    </Button>
                  </>
                ) : null}
              </Group>
              <Button variant="subtle" onClick={handleClose}>
                Close
              </Button>
            </Group>
          </Stack>
        ) : null}
      </Modal>

      <Modal
        opened={editingOpened}
        onClose={() => setEditingOpened(false)}
        title={activeTransaction ? `Edit Draft #${activeTransaction.id}` : 'Edit draft'}
        centered
      >
        <form
          onSubmit={(event) => void handleSubmit((values) => updateMutation.mutate(values))(event)}
        >
          <Stack gap="md">
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
                  <Select
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

            <Group justify="flex-end">
              <Button variant="subtle" onClick={() => setEditingOpened(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="default" loading={updateMutation.isPending}>
                Save changes
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </>
  );
};
