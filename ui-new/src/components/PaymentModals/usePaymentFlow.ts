import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { completeTransaction, createTransaction } from '@/api/transactions';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';
import type { CreateTransactionParams } from '@/api/transactions';

export type PaymentFlowState = {
  step: 'form' | 'confirm' | 'success';
  transactionId: number | null;
  amount: number;
  currency: string;
};

const initialState: PaymentFlowState = {
  step: 'form',
  transactionId: null,
  amount: 0,
  currency: 'GEL',
};

export type UsePaymentFlowOptions = {
  onSuccess?: () => void;
};

export const usePaymentFlow = (options?: UsePaymentFlowOptions) => {
  const [state, setState] = useState<PaymentFlowState>(initialState);
  const queryClient = useQueryClient();
  const actorEntity = useAuthStore((s) => s.actorEntity);

  const createMutation = useMutation({
    mutationFn: (params: CreateTransactionParams) => createTransaction(params),
    onSuccess: (data) => {
      setState((prev) => ({
        ...prev,
        step: 'confirm',
        transactionId: data.id,
        amount: parseFloat(data.amount),
        currency: data.currency,
      }));
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => completeTransaction(state.transactionId!),
    onSuccess: () => {
      setState((prev) => ({ ...prev, step: 'success' }));
      if (actorEntity) {
        void queryClient.invalidateQueries({
          queryKey: ['balances', actorEntity.id],
        });
      }
      options?.onSuccess?.();
    },
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: actorEntity !== null && state.step === 'success',
  });

  const submitForm = useCallback(
    (params: CreateTransactionParams) => {
      createMutation.mutate(params);
    },
    [createMutation]
  );

  const confirmTransaction = useCallback(() => {
    confirmMutation.mutate();
  }, [confirmMutation]);

  const cancelConfirm = useCallback(() => {
    setState((prev) => ({ ...prev, step: 'form' }));
  }, []);

  const closeSuccess = useCallback(() => {
    setState(initialState);
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  const getBalanceInfo = useCallback(() => {
    if (!balances || !state.currency) return { old: null, new: null };
    const currency = state.currency.toLowerCase();
    const currentBalance = balances.completed?.[currency];
    if (currentBalance === undefined) return { old: null, new: null };
    const currentNum = parseFloat(currentBalance);
    const newNum = currentNum;
    return {
      old: currentNum.toFixed(2),
      new: newNum.toFixed(2),
    };
  }, [balances, state.currency]);

  return {
    state,
    submitForm,
    confirmTransaction,
    cancelConfirm,
    closeSuccess,
    reset,
    getBalanceInfo,
    isCreating: createMutation.isPending,
    isConfirming: confirmMutation.isPending,
    createError: createMutation.error,
    confirmError: confirmMutation.error,
  };
};
