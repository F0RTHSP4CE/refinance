import {
  ActionIcon,
  Alert,
  Button,
  Group,
  NumberInput,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useFieldArray, useForm } from 'react-hook-form';
import { useEffect } from 'react';
import { z } from 'zod';
import { createInvoice, updateInvoice } from '@/api/invoices';
import { getEntities } from '@/api/entities';
import { getTags } from '@/api/tags';
import { CURRENCIES } from '@/constants/entities';
import type { Invoice } from '@/types/api';
import {
  AppModal,
  AppModalFooter,
  AppMonthField,
  AppMultiSelect,
  AppSelect,
  ModalStepHeader,
} from '@/components/ui';

const amountRowSchema = z.object({
  currency: z.enum(CURRENCIES),
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
});

const invoiceEditorSchema = z
  .object({
    from_entity_id: z.string().min(1, 'Select a source entity'),
    to_entity_id: z.string().min(1, 'Select a destination entity'),
    billing_period: z.string().optional(),
    comment: z.string().optional(),
    tag_ids: z.array(z.string()),
    amounts: z
      .array(amountRowSchema)
      .min(1, 'Add at least one invoice amount')
      .superRefine((rows, ctx) => {
        const currencies = rows.map((row) => row.currency);
        const uniqueCount = new Set(currencies).size;
        if (uniqueCount !== currencies.length) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'Each currency can only appear once.',
          });
        }
      }),
  })
  .refine((values) => values.from_entity_id !== values.to_entity_id, {
    message: 'From and to must be different entities.',
    path: ['to_entity_id'],
  });

type InvoiceEditorFormValues = z.infer<typeof invoiceEditorSchema>;

type InvoiceEditorModalProps = {
  opened: boolean;
  invoice?: Invoice | null;
  onClose: () => void;
  onSaved?: (invoice: Invoice) => void;
};

const MAX_ITEMS = 500;

const toBillingMonth = (value?: string | null) => {
  if (!value) return '';
  return value.slice(0, 7);
};

const getDefaultValues = (invoice?: Invoice | null): InvoiceEditorFormValues => ({
  from_entity_id: invoice ? String(invoice.from_entity_id) : '',
  to_entity_id: invoice ? String(invoice.to_entity_id) : '',
  billing_period: toBillingMonth(invoice?.billing_period),
  comment: invoice?.comment ?? '',
  tag_ids: invoice?.tags.map((tag) => String(tag.id)) ?? [],
  amounts: invoice?.amounts.map((entry) => ({
    currency: entry.currency.toUpperCase() as (typeof CURRENCIES)[number],
    amount: Number(entry.amount),
  })) ?? [{ currency: 'GEL', amount: 0 }],
});

export const InvoiceEditorModal = ({
  opened,
  invoice,
  onClose,
  onSaved,
}: InvoiceEditorModalProps) => {
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InvoiceEditorFormValues>({
    resolver: zodResolver(invoiceEditorSchema),
    defaultValues: getDefaultValues(invoice),
  });

  useEffect(() => {
    if (!opened) return;
    reset(getDefaultValues(invoice));
  }, [invoice, opened, reset]);

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'amounts',
  });

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'invoice-editor'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
    enabled: opened,
  });

  const tagsQuery = useQuery({
    queryKey: ['tags', 'invoice-editor'],
    queryFn: ({ signal }) => getTags({ limit: MAX_ITEMS, signal }),
    enabled: opened,
  });

  const invalidateInvoices = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['invoices'] }),
      queryClient.invalidateQueries({ queryKey: ['invoice'] }),
      queryClient.invalidateQueries({ queryKey: ['fees'] }),
      queryClient.invalidateQueries({ queryKey: ['pendingInvoices'] }),
    ]);
  };

  const saveMutation = useMutation({
    mutationFn: async (values: InvoiceEditorFormValues) => {
      const basePayload = {
        from_entity_id: Number(values.from_entity_id),
        to_entity_id: Number(values.to_entity_id),
        amounts: values.amounts.map((entry) => ({
          currency: entry.currency,
          amount: entry.amount,
        })),
        comment: values.comment?.trim() || undefined,
        tag_ids: values.tag_ids.map((tagId) => Number(tagId)),
      };

      if (invoice) {
        return updateInvoice(invoice.id, {
          ...basePayload,
          billing_period: values.billing_period?.trim()
            ? `${values.billing_period.trim()}-01`
            : null,
        });
      }

      return createInvoice({
        ...basePayload,
        billing_period: values.billing_period?.trim()
          ? `${values.billing_period.trim()}-01`
          : undefined,
      });
    },
    onSuccess: async (savedInvoice) => {
      await invalidateInvoices();
      onSaved?.(savedInvoice);
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

  const tagOptions =
    tagsQuery.data?.items
      .map((tag) => ({
        value: String(tag.id),
        label: tag.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  return (
    <AppModal
      opened={opened}
      onClose={onClose}
      title={invoice ? `Edit Invoice #${invoice.id}` : 'Create Invoice'}
      variant="detail"
      subtitle="Define participants, amounts, period, and tags in one invoice editing flow."
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
              form="invoice-editor-form"
              variant="default"
              loading={saveMutation.isPending}
            >
              {invoice ? 'Save changes' : 'Create invoice'}
            </Button>
          }
        />
      }
    >
      <form
        id="invoice-editor-form"
        onSubmit={(event) => void handleSubmit((values) => saveMutation.mutate(values))(event)}
      >
        <Stack gap="md">
          <ModalStepHeader
            eyebrow={invoice ? 'Invoice editor' : 'New invoice'}
            title={invoice ? `Invoice #${invoice.id}` : 'Create invoice'}
            description="Use multiple amount rows when the invoice can be settled in more than one currency."
          />
          <Group grow align="start">
            <Controller
              name="from_entity_id"
              control={control}
              render={({ field }) => (
                <AppSelect
                  label="From"
                  placeholder="Select payer"
                  searchable
                  data={entityOptions}
                  error={errors.from_entity_id?.message}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
            <Controller
              name="to_entity_id"
              control={control}
              render={({ field }) => (
                <AppSelect
                  label="To"
                  placeholder="Select receiver"
                  searchable
                  data={entityOptions}
                  error={errors.to_entity_id?.message}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
          </Group>

          <Controller
            name="billing_period"
            control={control}
            render={({ field }) => (
              <AppMonthField
                label="Billing period"
                value={field.value || ''}
                onChange={field.onChange}
              />
            )}
          />

          <Controller
            name="tag_ids"
            control={control}
            render={({ field }) => (
              <AppMultiSelect
                label="Tags"
                placeholder="Optional tags"
                data={tagOptions}
                searchable
                clearable
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />

          <Stack gap="xs">
            <Group justify="space-between" align="center">
              <Text size="sm" fw={600}>
                Amounts
              </Text>
              <Button
                variant="subtle"
                leftSection={<IconPlus size={14} />}
                type="button"
                onClick={() => append({ currency: 'USD', amount: 0 })}
              >
                Add amount
              </Button>
            </Group>

            {fields.map((fieldItem, index) => (
              <Group key={fieldItem.id} align="start" wrap="nowrap">
                <Controller
                  name={`amounts.${index}.amount`}
                  control={control}
                  render={({ field }) => (
                    <NumberInput
                      label={index === 0 ? 'Amount' : undefined}
                      min={0.01}
                      step={0.01}
                      decimalScale={2}
                      placeholder="0.00"
                      value={field.value}
                      onChange={(value) => field.onChange(typeof value === 'number' ? value : 0)}
                      error={errors.amounts?.[index]?.amount?.message}
                      flex={1}
                    />
                  )}
                />
                <Controller
                  name={`amounts.${index}.currency`}
                  control={control}
                  render={({ field }) => (
                    <AppSelect
                      label={index === 0 ? 'Currency' : undefined}
                      data={CURRENCIES.map((currency) => ({ value: currency, label: currency }))}
                      value={field.value}
                      onChange={field.onChange}
                      error={errors.amounts?.[index]?.currency?.message}
                      flex={1}
                    />
                  )}
                />
                <ActionIcon
                  type="button"
                  mt={index === 0 ? 24 : 0}
                  color="red"
                  variant="subtle"
                  aria-label={`Remove amount row ${index + 1}`}
                  onClick={() => remove(index)}
                  disabled={fields.length === 1}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
            ))}
            {errors.amounts?.root?.message ? (
              <Text size="xs" c="red">
                {errors.amounts.root.message}
              </Text>
            ) : null}
          </Stack>

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

          {saveMutation.isError ? (
            <Alert color="red" title="Could not save invoice">
              {saveMutation.error.message}
            </Alert>
          ) : null}
        </Stack>
      </form>
    </AppModal>
  );
};
