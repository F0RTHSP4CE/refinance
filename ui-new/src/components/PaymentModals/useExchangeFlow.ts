import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { executeExchange } from '@/api/currency-exchange';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';

export type ExchangeFlowState = {
  step: 'form' | 'preview' | 'success';
  previewData: {
    source_currency: string;
    source_amount: string;
    target_currency: string;
    target_amount: string;
    rate: string;
  } | null;
};

const initialState: ExchangeFlowState = {
  step: 'form',
  previewData: null,
};

export type UseExchangeFlowOptions = {
  onSuccess?: () => void;
};

export const useExchangeFlow = (options?: UseExchangeFlowOptions) => {
  const [state, setState] = useState<ExchangeFlowState>(initialState);
  const queryClient = useQueryClient();
  const actorEntity = useAuthStore((s) => s.actorEntity);

  const executeMutation = useMutation({
    mutationFn: executeExchange,
    onSuccess: async () => {
      if (actorEntity) {
        void queryClient.invalidateQueries({
          queryKey: ['balances', actorEntity.id],
        });
      }
      setState((prev) => ({ ...prev, step: 'success' }));
      options?.onSuccess?.();
    },
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: actorEntity !== null,
  });

  const setPreviewData = useCallback((data: any) => {
    setState((prev) => ({ ...prev, previewData: data }));
  }, []);

  const executeExchangeAction = useCallback((inputMode: 'source' | 'target') => {
    if (!state.previewData || !actorEntity) return;
    const { source_currency, target_currency, source_amount, target_amount } = state.previewData;

    executeMutation.mutate({
      entity_id: actorEntity.id,
      source_currency,
      target_currency,
      source_amount: inputMode === 'source' ? parseFloat(source_amount) : undefined,
      target_amount: inputMode === 'target' ? parseFloat(target_amount) : undefined,
    });
  }, [executeMutation, state.previewData, actorEntity]);

  const cancelPreview = useCallback(() => {
    setState((prev) => ({ ...prev, step: 'form', previewData: null }));
  }, []);

  const goToPreview = useCallback(() => {
    setState((prev) => ({ ...prev, step: 'preview' }));
  }, []);

  const closeSuccess = useCallback(() => {
    setState(initialState);
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  return {
    state,
    setPreviewData,
    executeExchange: executeExchangeAction,
    cancelPreview,
    goToPreview,
    closeSuccess,
    reset,
    balances,
    isExecuting: executeMutation.isPending,
    executeError: executeMutation.error,
  };
};
