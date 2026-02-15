import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Group, Modal, NumberInput, Select, Stack } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { createKeepzDeposit } from '@/api/deposits';
import { useAuthStore } from '@/stores/auth';

const CURRENCIES = [
  { value: 'GEL', label: 'GEL' },
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
] as const;

const cardTopUpSchema = z.object({
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(['GEL', 'USD', 'EUR']),
});

type CardTopUpFormValues = z.infer<typeof cardTopUpSchema>;

type CardTopUpModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const CardTopUpModal = ({ opened, onClose }: CardTopUpModalProps) => {
  const navigate = useNavigate();
  const actorEntity = useAuthStore((state) => state.actorEntity);

  const { control, handleSubmit, formState: { errors } } = useForm<CardTopUpFormValues>({
    resolver: zodResolver(cardTopUpSchema),
    defaultValues: { amount: 100, currency: 'GEL' },
  });

  const mutation = useMutation({
    mutationFn: (values: CardTopUpFormValues) =>
      createKeepzDeposit({
        to_entity_id: actorEntity!.id,
        amount: values.amount,
        currency: values.currency,
      }),
    onSuccess: (data) => {
      onClose();
      navigate(`/deposits/${data.id}`);
    },
  });

  const onSubmit = (values: CardTopUpFormValues) => {
    mutation.mutate(values);
  };

  if (!actorEntity) return null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Top up by card"
      centered
      closeOnClickOutside={false}
      closeOnEscape={false}
    >
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <Stack gap="md">
          <Controller
            name="amount"
            control={control}
            render={({ field }) => (
              <NumberInput
                label="Amount"
                placeholder="100"
                min={0.01}
                step={0.01}
                decimalScale={2}
                error={errors.amount?.message}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          <Controller
            name="currency"
            control={control}
            render={({ field }) => (
              <Select
                label="Currency"
                data={CURRENCIES}
                error={errors.currency?.message}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          {mutation.isError && (
            <Alert color="gray" title="Error">
              {mutation.error.message}
            </Alert>
          )}
          <Group justify="flex-end" gap="xs">
            <Button variant="subtle" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={mutation.isPending}>
              Top up
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export const CardTopUp = () => {
  const navigate = useNavigate();
  return (
    <CardTopUpModal
      opened
      onClose={() => navigate('/')}
    />
  );
};
