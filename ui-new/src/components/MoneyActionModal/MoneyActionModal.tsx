import {
  Alert,
  Button,
  Divider,
  Group,
  NumberInput,
  SimpleGrid,
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
import {
  AppSelect,
  AppModal,
  AppModalFooter,
  ModalStepHeader,
  SectionCard,
  StatusBadge,
} from '@/components/ui';

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
  const [reviewValues, setReviewValues] = useState<MoneyActionFormValues | null>(null);

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
  const entityLabelById = useMemo(
    () => new Map(entityOptions.map((entity) => [entity.value, entity.label])),
    [entityOptions]
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
    setReviewValues(null);
    onClose();
  };

  const modalTitle = title ?? (mode === 'request' ? 'Request money' : 'Create transfer');
  const modalDescription =
    description ??
    (mode === 'request'
      ? 'Create a pending invoice between any two people.'
      : 'Create a draft transfer between any two people.');
  const submitLabel = mode === 'request' ? 'Issue request' : 'Create transfer';
  const reviewValuesResolved =
    reviewValues ?? getDefaultValues(mode, actorEntity?.id, initialFromEntityId, initialToEntityId);
  const createdRecord = mode === 'request' ? createdInvoice : createdTransaction;
  const isSuccess = createdRecord != null;

  return (
    <AppModal
      opened={opened}
      onClose={handleCloseAll}
      variant={mode === 'request' ? 'form' : 'detail'}
      title={
        isSuccess ? (mode === 'request' ? 'Request created' : 'Transfer draft created') : modalTitle
      }
      subtitle={
        isSuccess
          ? mode === 'request'
            ? 'The invoice is ready and now visible in invoice workflows.'
            : 'The draft transfer is ready for review and completion.'
          : modalDescription
      }
      footer={
        isSuccess ? (
          <AppModalFooter primary={<Button onClick={handleCloseAll}>Close</Button>} />
        ) : reviewValues ? (
          <AppModalFooter
            aside={
              <Button variant="subtle" onClick={() => setReviewValues(null)}>
                Back to edit
              </Button>
            }
            secondary={
              <Button variant="subtle" onClick={handleCloseAll}>
                Cancel
              </Button>
            }
            primary={
              <Button
                variant="default"
                loading={createMutation.isPending}
                onClick={() => createMutation.mutate(reviewValuesResolved)}
              >
                {submitLabel}
              </Button>
            }
          />
        ) : (
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={handleCloseAll}>
                Cancel
              </Button>
            }
            primary={
              <Button type="submit" form={`money-action-${mode}-form`} variant="default">
                Review details
              </Button>
            }
          />
        )
      }
    >
      <Stack gap="lg">
        {isSuccess ? (
          <Stack gap="md">
            <ModalStepHeader
              eyebrow={mode === 'request' ? 'Invoice issued' : 'Draft created'}
              title={
                mode === 'request'
                  ? `Invoice #${createdInvoice?.id ?? ''}`
                  : `Transaction #${createdTransaction?.id ?? ''}`
              }
              description={
                mode === 'request'
                  ? 'Use this request in fee and profile flows without leaving the money action context.'
                  : 'Open it from transactions or profile activity when you are ready to complete it.'
              }
            />

            <SectionCard title="Summary" description="The created record now carries this context.">
              <Stack gap="sm">
                <Group justify="space-between" gap="md" align="start">
                  <Stack gap={4}>
                    <Text size="xs" tt="uppercase" className="app-muted-copy">
                      From
                    </Text>
                    <Text fw={700}>
                      {mode === 'request'
                        ? createdInvoice?.from_entity.name
                        : createdTransaction?.from_entity.name}
                    </Text>
                  </Stack>
                  <Stack gap={4} align="end">
                    <Text size="xs" tt="uppercase" className="app-muted-copy">
                      To
                    </Text>
                    <Text fw={700}>
                      {mode === 'request'
                        ? createdInvoice?.to_entity.name
                        : createdTransaction?.to_entity.name}
                    </Text>
                  </Stack>
                </Group>

                <Divider />

                <Group justify="space-between" gap="md" align="end">
                  <Stack gap={4}>
                    <Text size="xs" tt="uppercase" className="app-muted-copy">
                      Amount
                    </Text>
                    <Text size="2rem" fw={900}>
                      {mode === 'request'
                        ? `${createdInvoice?.amounts[0]?.amount ?? '0.00'} ${createdInvoice?.amounts[0]?.currency.toUpperCase() ?? 'GEL'}`
                        : `${createdTransaction?.amount ?? '0.00'} ${createdTransaction?.currency.toUpperCase() ?? 'GEL'}`}
                    </Text>
                  </Stack>
                  <StatusBadge tone={mode === 'request' ? 'warning' : 'draft'} size="lg">
                    {mode === 'request'
                      ? (createdInvoice?.status ?? 'pending')
                      : (createdTransaction?.status ?? 'draft')}
                  </StatusBadge>
                </Group>

                <Stack gap={4}>
                  <Text size="xs" tt="uppercase" className="app-muted-copy">
                    Comment
                  </Text>
                  <Text>
                    {(mode === 'request' ? createdInvoice?.comment : createdTransaction?.comment) ||
                      'No note added'}
                  </Text>
                </Stack>
              </Stack>
            </SectionCard>
          </Stack>
        ) : reviewValues ? (
          <Stack gap="lg">
            <ModalStepHeader
              eyebrow="Step 2"
              title="Review details"
              description="Check the participants, amount, and note before you create the record."
            />

            <Stack gap="md">
              <SectionCard
                title="Review details"
                description="Check the participants and amount before you create the record."
              >
                <Stack gap="sm">
                  <Group justify="space-between" align="start" gap="md">
                    <Stack gap={4}>
                      <Text size="xs" tt="uppercase" className="app-muted-copy">
                        From
                      </Text>
                      <Text fw={700}>
                        {entityLabelById.get(reviewValuesResolved.from_entity_id) || '—'}
                      </Text>
                    </Stack>
                    <Stack gap={4} align="end">
                      <Text size="xs" tt="uppercase" className="app-muted-copy">
                        To
                      </Text>
                      <Text fw={700}>
                        {entityLabelById.get(reviewValuesResolved.to_entity_id) || '—'}
                      </Text>
                    </Stack>
                  </Group>

                  <Divider />

                  <Group justify="space-between" align="end" gap="md">
                    <Stack gap={4}>
                      <Text size="xs" tt="uppercase" className="app-muted-copy">
                        Amount
                      </Text>
                      <Text size="2rem" fw={900}>
                        {reviewValuesResolved.amount.toFixed(2)} {reviewValuesResolved.currency}
                      </Text>
                    </Stack>
                    <Stack gap={4} align="end">
                      <Text size="xs" tt="uppercase" className="app-muted-copy">
                        Result
                      </Text>
                      <Text fw={700}>
                        {mode === 'request' ? 'Pending invoice' : 'Draft transfer'}
                      </Text>
                    </Stack>
                  </Group>

                  <Stack gap={4}>
                    <Text size="xs" tt="uppercase" className="app-muted-copy">
                      Comment
                    </Text>
                    <Text>{reviewValuesResolved.comment?.trim() || 'No note added'}</Text>
                  </Stack>
                </Stack>
              </SectionCard>

              {createMutation.isError ? (
                <Alert color="red" title={`Could not ${mode}`}>
                  {createMutation.error.message}
                </Alert>
              ) : null}
            </Stack>
          </Stack>
        ) : (
          <form
            id={`money-action-${mode}-form`}
            onSubmit={(event) => void handleSubmit((values) => setReviewValues(values))(event)}
          >
            <Stack gap="md">
              <ModalStepHeader
                eyebrow="Step 1"
                title={mode === 'request' ? 'Define the request' : 'Define the draft transfer'}
                description={
                  mode === 'request'
                    ? 'Set who owes whom, add the amount, and review it before issuing the invoice.'
                    : 'Set the parties, amount, and note. The transfer stays a draft until completed later.'
                }
              />

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <Controller
                  name="from_entity_id"
                  control={control}
                  render={({ field }) => (
                    <AppSelect
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
                    <AppSelect
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
              </SimpleGrid>

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
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
              </SimpleGrid>

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

              <Alert
                color="blue"
                title={mode === 'request' ? 'What happens next' : 'About this draft'}
              >
                {mode === 'request'
                  ? 'The request is created as a pending invoice and can be paid once funds are available.'
                  : 'The transfer is created as a draft so you can inspect it before completion.'}
              </Alert>
            </Stack>
          </form>
        )}
      </Stack>
    </AppModal>
  );
};
