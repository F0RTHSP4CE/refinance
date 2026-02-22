import { useCallback, useState } from 'react';
import {
  Alert,
  Button,
  Group,
  Image,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/stores/auth';
import { FRIDGE_PRESETS, CURRENCIES } from '@/constants/entities';
import { getServiceEntityIds } from '@/api/serviceEntities';
import { usePaymentFlow } from './usePaymentFlow';
import { ConfirmTransactionModal } from '@/components/ConfirmTransaction';
import { PaymentSuccessModal } from '@/components/PaymentSuccess';

const fridgePaySchema = z.object({
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(['GEL', 'USD', 'EUR']),
  comment: z.string().optional(),
});

type FridgePayFormValues = z.infer<typeof fridgePaySchema>;

type FridgePayModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const FridgePayModal = ({ opened, onClose }: FridgePayModalProps) => {
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
  } = usePaymentFlow({ onSuccess: () => { } });

  const {
    control,
    handleSubmit,
    setValue,
    watch,
    reset: resetForm,
  } = useForm<FridgePayFormValues>({
    resolver: zodResolver(fridgePaySchema),
    defaultValues: {
      amount: 5,
      currency: 'GEL',
      comment: '',
    },
  });

  const currency = watch('currency');
  const amount = watch('amount');
  const { data: serviceEntityIds } = useQuery({
    queryKey: ['service-entity-ids'],
    queryFn: ({ signal }) => getServiceEntityIds(signal),
    enabled: opened,
  });
  const fridgeEntityId = serviceEntityIds?.fridge ?? 141;

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
    (values: FridgePayFormValues) => {
      if (!actorEntity) return;
      submitForm({
        from_entity_id: actorEntity.id,
        to_entity_id: fridgeEntityId,
        amount: values.amount,
        currency: values.currency,
        comment: values.comment,
        status: 'draft',
      });
    },
    [actorEntity, fridgeEntityId, submitForm]
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

  return (
    <>
      <Modal
        opened={opened && state.step === 'form'}
        onClose={handleClose}
        title="Pay to Fridge"
        centered
      >
        <form onSubmit={(e) => void handleSubmit(handleFormSubmit)(e)}>
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Select a preset amount or enter a custom value.
            </Text>

            <Group gap="xs">
              {FRIDGE_PRESETS.map((preset) => (
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
                Other
              </Button>
            </Group>

            {isCustom && (
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
                    <Select
                      label="Currency"
                      data={CURRENCIES.map((c) => ({ value: c, label: c }))}
                      error={fieldState.error?.message}
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                      flex={3}
                    />
                  )}
                />
              </Group>
            )}

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

            {createError && (
              <Alert color="red" title="Error">
                {createError.message}
              </Alert>
            )}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" loading={isCreating} variant="default">
                Pay {amount} {currency}
              </Button>
            </Group>

            <Image src="/images/fridge.jpg" alt="Fridge" radius="md" mt="md" />
          </Stack>
        </form>
      </Modal>

      <ConfirmTransactionModal
        opened={state.step === 'confirm'}
        onConfirm={handleConfirmConfirm}
        onCancel={handleConfirmCancel}
        isLoading={isConfirming}
        amount={state.amount}
        currency={state.currency}
        direction="pay"
        targetName="Fridge"
      />

      <PaymentSuccessModal
        opened={state.step === 'success'}
        onClose={handleSuccessClose}
        amount={state.amount}
        currency={state.currency}
        oldBalance={balanceInfo.old}
        newBalance={balanceInfo.new}
      />
    </>
  );
};
