import { useCallback } from 'react';
import { Alert, Button, Image, Group, NumberInput, Stack, TextInput } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/stores/auth';
import { CURRENCIES } from '@/constants/entities';
import { getServiceEntityIds } from '@/api/serviceEntities';
import { usePaymentFlow } from './usePaymentFlow';
import { AppModal, AppModalFooter, AppSelect, ModalStepHeader, SectionCard } from '@/components/ui';

const reimburseSchema = z.object({
  source: z.enum(['fridge', 'coffee']),
  amount: z.number().min(0.01, 'Amount must be at least 0.01'),
  currency: z.enum(['GEL', 'USD', 'EUR']),
  comment: z.string().optional(),
});

type ReimburseFormValues = z.infer<typeof reimburseSchema>;

const SOURCE_OPTIONS = [
  { value: 'fridge', label: 'Fridge stash' },
  { value: 'coffee', label: 'Coffee stash' },
] as const;

type ReimburseModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const ReimburseModal = ({ opened, onClose }: ReimburseModalProps) => {
  const actorEntity = useAuthStore((s) => s.actorEntity);

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
    reset: resetForm,
  } = useForm<ReimburseFormValues>({
    resolver: zodResolver(reimburseSchema),
    defaultValues: {
      source: 'fridge',
      amount: 100,
      currency: 'GEL',
      comment: '',
    },
  });

  const source = useWatch({ control, name: 'source' });
  const { data: serviceEntityIds } = useQuery({
    queryKey: ['service-entity-ids'],
    queryFn: ({ signal }) => getServiceEntityIds(signal),
    enabled: opened,
  });
  const fridgeEntityId = serviceEntityIds?.fridge ?? 141;
  const coffeeEntityId = serviceEntityIds?.coffee ?? 150;

  const handleFormSubmit = useCallback(
    (values: ReimburseFormValues) => {
      if (!actorEntity) return;
      const sourceEntityId = values.source === 'fridge' ? fridgeEntityId : coffeeEntityId;
      submitForm({
        from_entity_id: sourceEntityId,
        to_entity_id: actorEntity.id,
        amount: values.amount,
        currency: values.currency,
        comment: values.comment,
        status: 'draft',
      });
    },
    [actorEntity, coffeeEntityId, fridgeEntityId, submitForm]
  );

  const handleClose = useCallback(() => {
    reset();
    resetForm();
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
  const sourceName = source === 'fridge' ? 'Fridge stash' : 'Coffee stash';
  const isFormStep = state.step === 'form';
  const isConfirmStep = state.step === 'confirm';
  const isSuccessStep = state.step === 'success';

  return (
    <AppModal
      opened={opened}
      onClose={handleClose}
      title={
        isSuccessStep
          ? 'Reimbursement complete'
          : isConfirmStep
            ? 'Review reimbursement'
            : 'Shared supplies reimbursement'
      }
      subtitle={
        isSuccessStep
          ? 'The reimbursement is complete and your balance is already refreshed.'
          : isConfirmStep
            ? 'Check the source, amount, and note before confirming this reimbursement.'
            : 'Recover fridge or coffee supply costs you covered for F0RTHSP4CE.'
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
              <Button type="submit" form="reimburse-form" loading={isCreating} variant="default">
                Review
              </Button>
            }
          />
        )
      }
    >
      {isFormStep ? (
        <form id="reimburse-form" onSubmit={(e) => void handleSubmit(handleFormSubmit)(e)}>
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Shared supplies"
              title="Shared supplies reimbursement"
              description="Choose the stash you refilled, set the amount, and review the reimbursement before it lands in your balance."
            />

            <Controller
              name="source"
              control={control}
              render={({ field, fieldState }) => (
                <AppSelect
                  label="Source stash"
                  data={SOURCE_OPTIONS}
                  error={fieldState.error?.message}
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            <Group align="flex-start">
              <Controller
                name="amount"
                control={control}
                render={({ field, fieldState }) => (
                  <NumberInput
                    label="Amount"
                    placeholder="100.00"
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

            <Controller
              name="comment"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Note"
                  placeholder="Optional note, for example: restocked drinks for March"
                  value={field.value || ''}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            {createError ? (
              <Alert color="red" title="Could not prepare the reimbursement">
                {createError.message}
              </Alert>
            ) : null}

            <Image src="/images/reimburse.jpg" alt="F0RTHSP4CE reimburse supplies" radius="md" />
          </Stack>
        </form>
      ) : null}

      {isConfirmStep ? (
        <Stack gap="md">
          <ModalStepHeader
            eyebrow="Review reimbursement"
            title={`${state.amount} ${state.currency.toUpperCase()}`}
            description={`You are about to receive funds back from the ${sourceName.toLowerCase()} stash.`}
          />
          <SectionCard title="What will happen">
            <Stack gap="sm">
              <Alert color="blue" title="Incoming reimbursement">
                This returns money from the {sourceName.toLowerCase()} stash to your balance and completes the transaction.
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
            description="The reimbursement is complete."
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
