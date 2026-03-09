import { useCallback, useState } from 'react';
import { Alert, Button, Image, Group, NumberInput, Stack, TextInput } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/stores/auth';
import { COFFEE_PRESETS, CURRENCIES } from '@/constants/entities';
import { getServiceEntityIds } from '@/api/serviceEntities';
import { usePaymentFlow } from './usePaymentFlow';
import { AppModal, AppModalFooter, AppSelect, ModalStepHeader, SectionCard } from '@/components/ui';

const coffeePaySchema = z.object({
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(['GEL', 'USD', 'EUR']),
  comment: z.string().optional(),
});

type CoffeePayFormValues = z.infer<typeof coffeePaySchema>;

type CoffeePayModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const CoffeePayModal = ({ opened, onClose }: CoffeePayModalProps) => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const [selectedPreset, setSelectedPreset] = useState<string>('5');
  const [isCustom, setIsCustom] = useState(false);

  const {
    state,
    submitForm,
    confirmTransaction,
    cancelConfirm,
    closeSuccess,
    reset,
    getBalanceInfo,
    isCreating,
    isConfirming,
    createError,
  } = usePaymentFlow({ onSuccess: () => {} });

  const {
    control,
    handleSubmit,
    setValue,
    reset: resetForm,
  } = useForm<CoffeePayFormValues>({
    resolver: zodResolver(coffeePaySchema),
    defaultValues: {
      amount: 5,
      currency: 'GEL',
      comment: '',
    },
  });

  const { data: serviceEntityIds } = useQuery({
    queryKey: ['service-entity-ids'],
    queryFn: ({ signal }) => getServiceEntityIds(signal),
    enabled: opened,
  });
  const coffeeEntityId = serviceEntityIds?.coffee ?? 150;

  const handlePresetClick = useCallback(
    (presetAmount: number) => {
      setSelectedPreset(String(presetAmount));
      setIsCustom(false);
      setValue('amount', presetAmount, { shouldValidate: true });
      setValue('currency', 'GEL');
    },
    [setValue]
  );

  const handleCustomClick = useCallback(() => {
    setIsCustom(true);
    setSelectedPreset('custom');
    setValue('amount', 15, { shouldValidate: true });
  }, [setValue]);

  const handleFormSubmit = useCallback(
    (values: CoffeePayFormValues) => {
      if (!actorEntity) return;
      submitForm({
        from_entity_id: actorEntity.id,
        to_entity_id: coffeeEntityId,
        amount: values.amount,
        currency: values.currency,
        comment: values.comment,
        status: 'draft',
      });
    },
    [actorEntity, coffeeEntityId, submitForm]
  );

  const handleClose = useCallback(() => {
    reset();
    resetForm();
    setSelectedPreset('5');
    setIsCustom(false);
    onClose();
  }, [reset, resetForm, onClose]);

  const handleConfirmConfirm = useCallback(() => {
    confirmTransaction();
  }, [confirmTransaction]);

  const handleConfirmCancel = useCallback(() => {
    cancelConfirm();
  }, [cancelConfirm]);

  const handleSuccessClose = useCallback(() => {
    closeSuccess();
    handleClose();
  }, [closeSuccess, handleClose]);

  if (!actorEntity) return null;

  const balanceInfo = getBalanceInfo();
  const isFormStep = state.step === 'form';
  const isConfirmStep = state.step === 'confirm';
  const isSuccessStep = state.step === 'success';

  return (
    <AppModal
      opened={opened}
      onClose={handleClose}
      title={
        isSuccessStep
          ? 'Coffee stash updated'
          : isConfirmStep
            ? 'Review payment'
            : 'Coffee stash'
      }
      subtitle={
        isSuccessStep
          ? 'The contribution is complete and your balance is already refreshed.'
          : isConfirmStep
            ? 'Check the stash, amount, and note before confirming this payment.'
            : 'Top up the shared coffee stash for beans, filters, and machine restocks.'
      }
      footer={
        isSuccessStep ? (
          <AppModalFooter
            primary={
              <Button variant="default" onClick={handleSuccessClose}>
                Done
              </Button>
            }
          />
        ) : isConfirmStep ? (
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={handleConfirmCancel}>
                Back
              </Button>
            }
            primary={
              <Button variant="default" onClick={handleConfirmConfirm} loading={isConfirming}>
                Confirm
              </Button>
            }
          />
        ) : (
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={handleClose}>
                Cancel
              </Button>
            }
            primary={
              <Button type="submit" form="coffee-pay-form" loading={isCreating} variant="default">
                Review
              </Button>
            }
          />
        )
      }
    >
      {isFormStep ? (
        <form id="coffee-pay-form" onSubmit={(e) => void handleSubmit(handleFormSubmit)(e)}>
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Shared supplies"
              title="Coffee stash"
              description="Pick a common amount or set a custom one, then review the payment before it leaves your balance."
            />

            <Group gap="xs">
              {COFFEE_PRESETS.map((preset) => (
                <Button
                  key={preset.amount}
                  variant={
                    selectedPreset === String(preset.amount) && !isCustom ? 'default' : 'light'
                  }
                  size="sm"
                  onClick={() => handlePresetClick(preset.amount)}
                  c={selectedPreset === String(preset.amount) && !isCustom ? undefined : 'dimmed'}
                >
                  {preset.label}
                </Button>
              ))}
              <Button
                variant={isCustom ? 'default' : 'light'}
                size="sm"
                onClick={handleCustomClick}
                c={isCustom ? undefined : 'dimmed'}
              >
                Custom
              </Button>
            </Group>

            {isCustom ? (
              <Group align="flex-start">
                <Controller
                  name="amount"
                  control={control}
                  render={({ field, fieldState }) => (
                    <NumberInput
                      label="Amount"
                      placeholder="5.00"
                      min={0.01}
                      step={0.01}
                      decimalScale={2}
                      error={fieldState.error?.message}
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
                  render={({ field, fieldState }) => (
                    <AppSelect
                      label="Currency"
                      data={CURRENCIES.map((item) => ({ value: item, label: item }))}
                      error={fieldState.error?.message}
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                      flex={3}
                    />
                  )}
                />
              </Group>
            ) : null}

            <Controller
              name="comment"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Note"
                  placeholder="Optional note for the coffee stash"
                  value={field.value || ''}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            {createError ? (
              <Alert color="red" title="Could not prepare the contribution">
                {createError.message}
              </Alert>
            ) : null}

            <Image src="/images/coffee.jpg" alt="F0RTHSP4CE coffee stash" radius="md" />
          </Stack>
        </form>
      ) : null}

      {isConfirmStep ? (
        <Stack gap="md">
          <ModalStepHeader
            eyebrow="Review payment"
            title={`${state.amount} ${state.currency.toUpperCase()}`}
            description="You are about to pay into the shared coffee stash."
          />
          <SectionCard title="What will happen">
            <Stack gap="sm">
              <Alert color="blue" title="Outgoing payment">
                This moves money from your balance to the coffee stash and marks the payment as completed.
              </Alert>
            </Stack>
          </SectionCard>
        </Stack>
      ) : null}

      {isSuccessStep ? (
        <Stack gap="md">
          <ModalStepHeader
            eyebrow="Completed"
            title={`${state.amount} ${state.currency.toUpperCase()}`}
            description="The coffee stash payment is complete."
          />
          {balanceInfo.old && balanceInfo.new ? (
            <SectionCard title="Balance update">
              <Stack gap={4}>
                <div className="app-muted-copy">
                  Before: {balanceInfo.old} {state.currency.toUpperCase()}
                </div>
                <div>
                  Now: {balanceInfo.new} {state.currency.toUpperCase()}
                </div>
              </Stack>
            </SectionCard>
          ) : null}
        </Stack>
      ) : null}
    </AppModal>
  );
};
