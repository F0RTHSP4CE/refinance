import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useEffect, useMemo, useState } from 'react';
import { z } from 'zod';
import { createInvoice } from '@/api/invoices';
import { createTransaction } from '@/api/transactions';
import { getEntities } from '@/api/entities';
import { CURRENCIES } from '@/constants/entities';
import { useAuthStore } from '@/stores/auth';
import type { Invoice, Transaction } from '@/types/api';
import { InvoiceDetailsModal } from '@/components/Invoices/InvoiceDetailsModal';
import { TransactionDetailsModal } from '@/components/Transactions/TransactionDetailsModal';

const moneyActionSchema = z
  .object({
    from_entity_id: z.string().min(1, 'Select who pays or owes'),
    to_entity_id: z.string().min(1, 'Select who receives'),
    amount: z.number().min(0.01, 'Amount must be at least 0.01'),
    currency: z.enum(CURRENCIES),
    comment: z.string().optional(),
  })
  .refine((values) => values.from_entity_id !== values.to_entity_id, {
    message: 'From and to must be different entities.',
    path: ['to_entity_id'],
  });

type MoneyActionFormValues = z.infer<typeof moneyActionSchema>;

export type MoneyActionMode = 'transfer' | 'request';

type MoneyActionModalProps = {
  opened: boolean;
  mode: MoneyActionMode;
  onClose: () => void;
  initialFromEntityId?: number | null;
  initialToEntityId?: number | null;
  title?: string;
  description?: string;
};

const MAX_ITEMS = 500;

const getDefaultValues = (
  mode: MoneyActionMode,
  actorEntityId?: number | null,
  initialFromEntityId?: number | null,
  initialToEntityId?: number | null
): MoneyActionFormValues => ({
  from_entity_id:
    initialFromEntityId != null
      ? String(initialFromEntityId)
      : mode === 'transfer' && actorEntityId != null
        ? String(actorEntityId)
        : '',
  to_entity_id:
    initialToEntityId != null
      ? String(initialToEntityId)
      : mode === 'request' && actorEntityId != null
        ? String(actorEntityId)
        : '',
  amount: 0,
  currency: 'GEL',
  comment: '',
});

export const MoneyActionModal = ({
  opened,
  mode,
  onClose,
  initialFromEntityId,
  initialToEntityId,
  title,
  description,
}: MoneyActionModalProps) => {
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const queryClient = useQueryClient();
  const [createdInvoice, setCreatedInvoice] = useState<Invoice | null>(null);
  const [createdTransaction, setCreatedTransaction] = useState<Transaction | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<MoneyActionFormValues>({
    resolver: zodResolver(moneyActionSchema),
    defaultValues: getDefaultValues(mode, actorEntity?.id, initialFromEntityId, initialToEntityId),
  });

  useEffect(() => {
    if (!opened) return;
    reset(getDefaultValues(mode, actorEntity?.id, initialFromEntityId, initialToEntityId));
  }, [actorEntity?.id, initialFromEntityId, initialToEntityId, mode, opened, reset]);

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'money-action-modal'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
    enabled: opened,
  });

  const entityOptions = useMemo(
    () =>
      entitiesQuery.data?.items
        .map((entity) => ({
          value: String(entity.id),
          label: entity.name,
        }))
        .sort((left, right) => left.label.localeCompare(right.label)) ?? [],
    [entitiesQuery.data?.items]
  );

  const createMutation = useMutation({
    mutationFn: async (values: MoneyActionFormValues) => {
      const payload = {
        from_entity_id: Number(values.from_entity_id),
        to_entity_id: Number(values.to_entity_id),
        amount: values.amount,
        currency: values.currency,
        comment: values.comment?.trim() || undefined,
      };

      if (mode === 'request') {
        return createInvoice({
          from_entity_id: payload.from_entity_id,
          to_entity_id: payload.to_entity_id,
          amounts: [{ currency: payload.currency, amount: payload.amount }],
          comment: payload.comment,
        });
      }

      return createTransaction({
        from_entity_id: payload.from_entity_id,
        to_entity_id: payload.to_entity_id,
        amount: payload.amount,
        currency: payload.currency,
        comment: payload.comment,
        status: 'draft',
      });
    },
    onSuccess: async (created) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['balances'] }),
        queryClient.invalidateQueries({ queryKey: ['pendingInvoices'] }),
        queryClient.invalidateQueries({ queryKey: ['fees'] }),
      ]);

      if (mode === 'request') {
        setCreatedInvoice(created as Invoice);
        return;
      }

      setCreatedTransaction(created as Transaction);
    },
  });

  const handleCloseAll = () => {
    reset(getDefaultValues(mode, actorEntity?.id, initialFromEntityId, initialToEntityId));
    setCreatedInvoice(null);
    setCreatedTransaction(null);
    onClose();
  };

  const modalTitle = title ?? (mode === 'request' ? 'Request money' : 'Create transfer');
  const modalDescription =
    description ??
    (mode === 'request'
      ? 'Create a pending invoice between any two people.'
      : 'Create a draft transfer between any two people.');

  return (
    <>
      <Modal
        opened={opened && createdInvoice == null && createdTransaction == null}
        onClose={handleCloseAll}
        title={modalTitle}
        centered
      >
        <form
          onSubmit={(event) => void handleSubmit((values) => createMutation.mutate(values))(event)}
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {modalDescription}
            </Text>

            <Group grow align="start">
              <Controller
                name="from_entity_id"
                control={control}
                render={({ field }) => (
                  <Select
                    label="From"
                    placeholder="Select source entity"
                    searchable
                    data={entityOptions}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.from_entity_id?.message}
                  />
                )}
              />
              <Controller
                name="to_entity_id"
                control={control}
                render={({ field }) => (
                  <Select
                    label="To"
                    placeholder="Select destination entity"
                    searchable
                    data={entityOptions}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.to_entity_id?.message}
                  />
                )}
              />
            </Group>

            <Group grow align="start">
              <Controller
                name="amount"
                control={control}
                render={({ field }) => (
                  <NumberInput
                    label="Amount"
                    placeholder="0.00"
                    min={0.01}
                    step={0.01}
                    decimalScale={2}
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

            {createMutation.isError ? (
              <Alert color="red" title={`Could not ${mode}`}>
                {createMutation.error.message}
              </Alert>
            ) : null}

            <Group justify="flex-end">
              <Button variant="subtle" onClick={handleCloseAll}>
                Cancel
              </Button>
              <Button type="submit" variant="default" loading={createMutation.isPending}>
                {mode === 'request' ? 'Create request' : 'Create transfer'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <InvoiceDetailsModal
        opened={opened && createdInvoice != null}
        invoice={createdInvoice}
        onClose={handleCloseAll}
      />

      <TransactionDetailsModal
        opened={opened && createdTransaction != null}
        transaction={createdTransaction}
        onClose={handleCloseAll}
      />
    </>
  );
};
