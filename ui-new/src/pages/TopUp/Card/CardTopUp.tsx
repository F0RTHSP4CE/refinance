import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, NumberInput, Stack } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { createKeepzDeposit } from '@/api/deposits';
import { useAuthStore } from '@/stores/auth';
import { AppModal, AppModalFooter, AppSelect, ModalStepHeader } from '@/components/ui';

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

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CardTopUpFormValues>({
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
    <AppModal
      opened={opened}
      onClose={onClose}
      title="Top up by card"
      subtitle="Create a payment handoff and continue on the deposit status page."
      closeOnClickOutside={false}
      closeOnEscape={false}
      footer={
        <AppModalFooter
          secondary={
            <Button variant="subtle" onClick={onClose}>
              Cancel
            </Button>
          }
          primary={
            <Button type="submit" form="card-top-up-form" loading={mutation.isPending}>
              Top up
            </Button>
          }
        />
      }
    >
      <form id="card-top-up-form" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <Stack gap="md">
          <ModalStepHeader
            eyebrow="Card payment"
            title="Start a top-up"
            description="Pick the amount and currency, then continue on the hosted payment flow."
          />
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
              <AppSelect
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
        </Stack>
      </form>
    </AppModal>
  );
};

export const CardTopUp = () => {
  const navigate = useNavigate();
  return <CardTopUpModal opened onClose={() => navigate('/')} />;
};
