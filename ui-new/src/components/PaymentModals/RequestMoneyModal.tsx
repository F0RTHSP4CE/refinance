import { useCallback, useState } from 'react';
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
  type ComboboxItem,
  Loader,
} from '@mantine/core';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useDebouncedValue } from '@mantine/hooks';
import { useAuthStore } from '@/stores/auth';
import { CURRENCIES } from '@/constants/entities';
import { createInvoice } from '@/api/invoices';
import { getEntities } from '@/api/entities';
import type { Entity } from '@/types/api';

const requestMoneySchema = z.object({
  from_entity_id: z.string().min(1, 'Please select a user'),
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(['GEL', 'USD', 'EUR']),
  comment: z.string().optional(),
});

type RequestMoneyFormValues = z.infer<typeof requestMoneySchema>;

type RequestMoneyModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const RequestMoneyModal = ({ opened, onClose }: RequestMoneyModalProps) => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearch] = useDebouncedValue(searchValue, 300);
  const [success, setSuccess] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm<RequestMoneyFormValues>({
    resolver: zodResolver(requestMoneySchema),
    defaultValues: {
      amount: 0,
      currency: 'GEL',
      comment: '',
    },
  });

  const { data: entities, isLoading: isLoadingEntities } = useQuery({
    queryKey: ['entities', debouncedSearch],
    queryFn: ({ signal }) =>
      getEntities({
        name: debouncedSearch,
        limit: 20,
        signal,
      }),
    enabled: opened,
  });

  const createMutation = useMutation({
    mutationFn: createInvoice,
    onSuccess: () => {
      setSuccess(true);
    },
  });

  const getSelectOptions = useCallback((): ComboboxItem[] => {
    if (!entities?.items) return [];
    return entities.items
      .filter((e: Entity) => e.id !== actorEntity?.id)
      .map((e: Entity) => ({
        value: String(e.id),
        label: e.name,
      }));
  }, [entities, actorEntity]);

  const handleFormSubmit = useCallback(
    (values: RequestMoneyFormValues) => {
      if (!actorEntity) return;
      const selectedEntityId = Number.parseInt(values.from_entity_id, 10);
      const isValidSelection = getSelectOptions().some((option) => option.value === values.from_entity_id);
      if (Number.isNaN(selectedEntityId) || !isValidSelection || selectedEntityId === actorEntity.id) {
        setError('from_entity_id', {
          type: 'manual',
          message: 'Please select a valid user from the list',
        });
        return;
      }
      clearErrors('from_entity_id');
      createMutation.mutate({
        from_entity_id: selectedEntityId,
        to_entity_id: actorEntity.id,
        amounts: [{ currency: values.currency, amount: values.amount }],
        // billing_period is optional
      });
    },
    [actorEntity, clearErrors, createMutation, getSelectOptions, setError]
  );

  const handleClose = useCallback(() => {
    reset();
    setSuccess(false);
    setSearchValue('');
    onClose();
  }, [reset, onClose]);

  if (!actorEntity) return null;

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Request Money"
      centered
    >
      {!success ? (
        <form onSubmit={(e) => void handleSubmit(handleFormSubmit)(e)}>
          <Stack gap="md">
            <Controller
              name="from_entity_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="From User"
                  placeholder="Search user..."
                  data={getSelectOptions()}
                  searchable
                  searchValue={searchValue}
                  onSearchChange={setSearchValue}
                  nothingFoundMessage={
                    isLoadingEntities ? <Loader size="xs" /> : 'No users found'
                  }
                  error={errors.from_entity_id?.message}
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  filter={({ options, search: _search }) => {
                    // Server-side filtering, so we just return everything or rely on server
                    // But Select component needs filtering if we provide data
                    // Since we fetch based on search, the data should already be filtered
                    return options;
                  }}
                />
              )}
            />

            <Group align="flex-start">
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
                    error={errors.amount?.message}
                    value={field.value}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    flex={7}
                  />
                )}
              />
              <Controller
                name="currency"
                control={control}
                render={({ field }) => (
                  <Select
                    label="Currency"
                    data={CURRENCIES.map((c) => ({ value: c, label: c }))}
                    error={errors.currency?.message}
                    value={field.value}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    flex={3}
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
                  placeholder="optional"
                  value={field.value || ''}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            {createMutation.isError && (
              <Alert color="red" title="Error">
                Failed to create request. {createMutation.error.message}
              </Alert>
            )}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending} variant="default">
                Request
              </Button>
            </Group>
          </Stack>
        </form>
      ) : (
        <Stack align="center" gap="md" py="md">
          <Text size="lg" fw={700}>
            Request Sent!
          </Text>
          <Text c="dimmed" ta="center">
            Your request has been sent successfully.
          </Text>
          <Button onClick={handleClose} variant="default">
            Close
          </Button>
        </Stack>
      )}
    </Modal>
  );
};
