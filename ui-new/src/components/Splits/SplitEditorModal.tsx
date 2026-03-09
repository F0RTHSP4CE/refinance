import { Alert, Button, NumberInput, SimpleGrid, Stack, TextInput } from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useEffect } from 'react';
import { z } from 'zod';
import { getEntities } from '@/api/entities';
import { createSplit, updateSplit } from '@/api/splits';
import { CURRENCIES } from '@/constants/entities';
import { useAuthStore } from '@/stores/auth';
import type { Split } from '@/types/api';
import { AppModal, AppModalFooter, AppSelect, ModalStepHeader } from '@/components/ui';

const splitEditorSchema = z.object({
  name: z.string().optional(),
  recipient_entity_id: z.string().min(1, 'Select a recipient'),
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(CURRENCIES),
});

type SplitEditorFormValues = z.infer<typeof splitEditorSchema>;

type SplitEditorModalProps = {
  opened: boolean;
  split?: Split | null;
  onClose: () => void;
  onSaved?: (split: Split) => void;
};

const MAX_ITEMS = 500;

const getDefaultValues = (
  split: Split | null | undefined,
  actorEntityId?: number
): SplitEditorFormValues => ({
  name: split?.comment ?? '',
  recipient_entity_id: split
    ? String(split.recipient_entity.id)
    : actorEntityId
      ? String(actorEntityId)
      : '',
  amount: split ? Number(split.amount) : 0,
  currency: (split?.currency.toUpperCase() as (typeof CURRENCIES)[number]) ?? 'GEL',
});

export const SplitEditorModal = ({ opened, split, onClose, onSaved }: SplitEditorModalProps) => {
  const queryClient = useQueryClient();
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SplitEditorFormValues>({
    resolver: zodResolver(splitEditorSchema),
    defaultValues: getDefaultValues(split, actorEntity?.id),
  });

  useEffect(() => {
    if (!opened) return;
    reset(getDefaultValues(split, actorEntity?.id));
  }, [actorEntity?.id, opened, reset, split]);

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'split-editor'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
    enabled: opened,
  });

  const saveMutation = useMutation({
    mutationFn: async (values: SplitEditorFormValues) => {
      const payload = {
        recipient_entity_id: Number(values.recipient_entity_id),
        amount: values.amount,
        currency: values.currency,
        comment: values.name?.trim() || undefined,
      };
      if (split) {
        return updateSplit(split.id, payload);
      }
      return createSplit(payload);
    },
    onSuccess: async (savedSplit) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['splits'] }),
        queryClient.invalidateQueries({ queryKey: ['split', savedSplit.id] }),
      ]);
      onSaved?.(savedSplit);
      onClose();
    },
  });

  const entityOptions =
    entitiesQuery.data?.items
      .map((entity) => ({
        value: String(entity.id),
        label: entity.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title={split ? `Edit ${split.comment || `Split #${split.id}`}` : 'Create split'}
      subtitle="Define the recipient, total amount, and split label before participants are added."
      footer={
        <AppModalFooter
          secondary={
            <Button variant="subtle" onClick={onClose}>
              Cancel
            </Button>
          }
          primary={
            <Button
              type="submit"
              form="split-editor-form"
              variant="default"
              loading={saveMutation.isPending}
            >
              {split ? 'Save changes' : 'Create split'}
            </Button>
          }
        />
      }
    >
      <form
        id="split-editor-form"
        onSubmit={(event) => void handleSubmit((values) => saveMutation.mutate(values))(event)}
      >
        <Stack gap="md">
          <ModalStepHeader
            eyebrow={split ? 'Split editor' : 'New split'}
            title={split ? split.comment || `Split #${split.id}` : 'Create split'}
            description="Give the split a recognizable name, choose the recipient, and set the total amount to collect from participants."
          />

          <Controller
            name="name"
            control={control}
            render={({ field }) => (
              <TextInput
                label="Name"
                placeholder="Utilities for March"
                value={field.value || ''}
                onChange={field.onChange}
              />
            )}
          />

          <Controller
            name="recipient_entity_id"
            control={control}
            render={({ field }) => (
              <AppSelect
                label="Recipient"
                placeholder="Select recipient"
                searchable
                data={entityOptions}
                value={field.value}
                onChange={field.onChange}
                error={errors.recipient_entity_id?.message}
              />
            )}
          />

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Controller
              name="amount"
              control={control}
              render={({ field }) => (
                <NumberInput
                  label="Amount"
                  min={0.01}
                  step={0.01}
                  decimalScale={2}
                  placeholder="10.00"
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

          {saveMutation.isError ? (
            <Alert color="red" title="Could not save split">
              {saveMutation.error.message}
            </Alert>
          ) : null}
        </Stack>
      </form>
    </AppModal>
  );
};
