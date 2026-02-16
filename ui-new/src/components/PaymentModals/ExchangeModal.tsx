import { ActionIcon, Alert, Button, Group, Modal, NumberInput, Select, Stack, Text } from '@mantine/core';
import { IconArrowDown, IconArrowRight, IconExchange as TablerIconExchange } from '@tabler/icons-react';
import { useState, useMemo } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/auth';
import { useExchangeFlow } from './useExchangeFlow';
import { PaymentSuccessModal } from '../PaymentSuccess';
import { getBalances } from '@/api/balance';
import { getExchangeRates } from '@/api/currency-exchange';
import { z } from 'zod';

const CURRENCIES = [
  { value: 'GEL', label: 'GEL' },
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
] as const;

const exchangeSchema = z.object({
  sourceCurrency: z.enum(['GEL', 'USD', 'EUR']),
  targetCurrency: z.enum(['GEL', 'USD', 'EUR']),
  sourceAmount: z.number().min(0.01, 'Amount must be at least 0.01').optional(),
  targetAmount: z.number().min(0.01, 'Amount must be at least 0.01').optional(),
}).refine((data) => data.sourceCurrency !== data.targetCurrency, {
  message: 'Source and target currencies must be different',
  path: ['targetCurrency'],
});

type ExchangeFormValues = z.infer<typeof exchangeSchema>;

type ExchangeModalProps = {
  opened: boolean;
  onClose: () => void;
};

type RatesData = {
  code: string;
  rate: string;
  quantity: string;
}[];

function getExchangeRate(
  sourceCurrency: string,
  targetCurrency: string,
  rates: RatesData
): number | null {
  if (sourceCurrency === targetCurrency) return null;

  const getCurrencyInfo = (code: string) => {
    if (code.toLowerCase() === 'gel') {
      return { rate: 1, quantity: 1 };
    }
    const cur = rates.find((c) => c.code.toLowerCase() === code.toLowerCase());
    if (!cur) return null;
    return { rate: parseFloat(cur.rate), quantity: parseFloat(cur.quantity) };
  };

  const sourceInfo = getCurrencyInfo(sourceCurrency);
  const targetInfo = getCurrencyInfo(targetCurrency);
  if (!sourceInfo || !targetInfo) return null;

  const gelPerSource = sourceInfo.rate / sourceInfo.quantity;
  const gelPerTarget = targetInfo.rate / targetInfo.quantity;
  const conversionRate = gelPerSource / gelPerTarget;

  return Math.floor(conversionRate * 100) / 100;
}

function calculateConversion(
  sourceAmount: number | undefined,
  targetAmount: number | undefined,
  sourceCurrency: string,
  targetCurrency: string,
  rates: RatesData
): { sourceAmount: number; targetAmount: number; rate: number } | null {
  if (!sourceAmount && !targetAmount) return null;
  if (sourceCurrency === targetCurrency) return null;

  const getCurrencyInfo = (code: string) => {
    if (code.toLowerCase() === 'gel') {
      return { rate: 1, quantity: 1 };
    }
    const cur = rates.find((c) => c.code.toLowerCase() === code.toLowerCase());
    if (!cur) return null;
    return { rate: parseFloat(cur.rate), quantity: parseFloat(cur.quantity) };
  };

  const sourceInfo = getCurrencyInfo(sourceCurrency);
  const targetInfo = getCurrencyInfo(targetCurrency);
  if (!sourceInfo || !targetInfo) return null;

  const gelPerSource = sourceInfo.rate / sourceInfo.quantity;
  const gelPerTarget = targetInfo.rate / targetInfo.quantity;
  const conversionRate = gelPerSource / gelPerTarget;
  const displayRate = conversionRate;

  if (sourceAmount && !targetAmount) {
    return {
      sourceAmount,
      targetAmount: Math.floor(sourceAmount * conversionRate * 100) / 100,
      rate: Math.floor(displayRate * 100) / 100,
    };
  } else if (targetAmount && !sourceAmount) {
    return {
      sourceAmount: Math.floor((targetAmount / conversionRate) * 100) / 100,
      targetAmount,
      rate: Math.floor(displayRate * 100) / 100,
    };
  }
  return null;
}

export const ExchangeModal = ({ opened, onClose }: ExchangeModalProps) => {
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const { state, setPreviewData, executeExchange, cancelPreview, closeSuccess, isExecuting, executeError } = useExchangeFlow({
    onSuccess: onClose,
  });

  const { data: freshBalances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: actorEntity !== null,
  });

  const { data: ratesData } = useQuery({
    queryKey: ['exchange-rates'],
    queryFn: () => getExchangeRates() as Promise<{ currencies: RatesData }[]>,
    staleTime: Infinity,
  });

  const rates = useMemo(() => ratesData?.[0]?.currencies ?? [], [ratesData]);

  const [inputMode, setInputMode] = useState<'source' | 'target'>('source');
  const [balancesBeforeExchange, setBalancesBeforeExchange] = useState<Record<string, number>>({});

  const { control, watch, setValue, formState: { errors } } = useForm<ExchangeFormValues>({
    resolver: zodResolver(exchangeSchema),
    defaultValues: {
      sourceCurrency: 'USD',
      targetCurrency: 'GEL',
      sourceAmount: undefined,
      targetAmount: undefined,
    },
  });

  const sourceCurrency = watch('sourceCurrency');
  const targetCurrency = watch('targetCurrency');
  const sourceAmount = watch('sourceAmount');
  const targetAmount = watch('targetAmount');

  const getBalance = (currency: string): number => {
    const key = currency.toLowerCase() as keyof NonNullable<typeof freshBalances>['completed'];
    return freshBalances?.completed?.[key] ? parseFloat(freshBalances.completed[key]) : 0;
  };

  const conversion = useMemo(() => {
    if (!inputMode) return null;
    return calculateConversion(
      inputMode === 'source' ? sourceAmount : undefined,
      inputMode === 'target' ? targetAmount : undefined,
      sourceCurrency,
      targetCurrency,
      rates
    );
  }, [sourceAmount, targetAmount, sourceCurrency, targetCurrency, inputMode, rates]);

  const exchangeRate = useMemo(() => {
    return getExchangeRate(sourceCurrency, targetCurrency, rates);
  }, [sourceCurrency, targetCurrency, rates]);

  const handleGoToPreview = () => {
    if (!conversion) return;
    setBalancesBeforeExchange({
      [sourceCurrency]: getBalance(sourceCurrency),
      [targetCurrency]: getBalance(targetCurrency),
    });
    setPreviewData({
      source_currency: sourceCurrency,
      source_amount: conversion.sourceAmount.toString(),
      target_currency: targetCurrency,
      target_amount: conversion.targetAmount.toString(),
      rate: conversion.rate.toString(),
    });
  };

  const handleSourceAmountChange = (value: number | string) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    setValue('sourceAmount', numValue || undefined);
    setValue('targetAmount', undefined);
    setInputMode('source');
  };

  const handleTargetAmountChange = (value: number | string) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    setValue('targetAmount', numValue || undefined);
    setValue('sourceAmount', undefined);
    setInputMode('target');
  };

  const handleSourceCurrencyChange = (value: string) => {
    if (value === targetCurrency) {
      setValue('sourceCurrency', targetCurrency);
      setValue('targetCurrency', sourceCurrency);
    } else {
      setValue('sourceCurrency', value as 'GEL' | 'USD' | 'EUR');
    }
  };

  const handleTargetCurrencyChange = (value: string) => {
    if (value === sourceCurrency) {
      setValue('targetCurrency', sourceCurrency);
      setValue('sourceCurrency', targetCurrency);
    } else {
      setValue('targetCurrency', value as 'GEL' | 'USD' | 'EUR');
    }
  };

  const swapCurrencies = () => {
    const currentAmount = inputMode === 'source' ? sourceAmount : targetAmount;

    setValue('sourceCurrency', targetCurrency);
    setValue('targetCurrency', sourceCurrency);

    if (currentAmount) {
      if (inputMode === 'source') {
        setValue('sourceAmount', currentAmount);
        setValue('targetAmount', undefined);
      } else {
        setValue('targetAmount', currentAmount);
        setValue('sourceAmount', undefined);
      }
    } else {
      setValue('sourceAmount', undefined);
      setValue('targetAmount', undefined);
    }
  };

  if (!actorEntity) return null;

  return (
    <>
      <Modal
        opened={opened && state.step !== 'success'}
        onClose={onClose}
        title={state.step === 'form' ? 'Exchange' : 'Confirm Exchange'}
        centered
        closeOnClickOutside={state.step === 'form'}
        closeOnEscape={state.step === 'form'}
      >
        {state.step === 'form' && (
          <form onSubmit={(e) => { e.preventDefault(); handleGoToPreview(); }}>
            <Stack gap="md">
              <Group align="flex-start">
                <Stack gap={4} flex={1}>
                  <Text size="xs" c="dimmed" fw={600}>From</Text>
                  <Controller
                    name="sourceAmount"
                    control={control}
                    render={({ field }) => (
                      <NumberInput
                        placeholder="0.00"
                        min={0.01}
                        step={0.01}
                        decimalScale={2}
                        error={errors.sourceAmount?.message}
                        value={inputMode === 'target' && conversion ? conversion.sourceAmount : field.value}
                        onChange={handleSourceAmountChange}
                        flex={1}
                        size="lg"
                        styles={{ input: { fontSize: '24px', fontWeight: 700 } }}
                      />
                    )}
                  />
                  <Controller
                    name="sourceCurrency"
                    control={control}
                    render={({ field }) => (
                      <Select
                        data={CURRENCIES}
                        error={errors.sourceCurrency?.message}
                        value={field.value}
                        onChange={(value) => handleSourceCurrencyChange(value as string)}
                      />
                    )}
                   />
                  <Text size="xs" c="dimmed">
                    Balance: {getBalance(sourceCurrency).toFixed(2)} {sourceCurrency}
                  </Text>
                  <Text size="xs" c="dimmed" opacity={conversion ? 1 : 0}>
                    {conversion ? `→ ${(getBalance(sourceCurrency) - conversion.sourceAmount).toFixed(2)} ${sourceCurrency}` : '−'}
                  </Text>
                </Stack>

                <ActionIcon variant="light" size="lg" onClick={swapCurrencies} mt={32}>
                  <IconArrowDown size={20} />
                </ActionIcon>

                <Stack gap={4} flex={1}>
                  <Text size="xs" c="dimmed" fw={600}>To</Text>
                  <Controller
                    name="targetAmount"
                    control={control}
                    render={({ field }) => (
                      <NumberInput
                        placeholder="0.00"
                        min={0.01}
                        step={0.01}
                        decimalScale={2}
                        error={errors.targetAmount?.message}
                        value={inputMode === 'source' && conversion ? conversion.targetAmount : field.value}
                        onChange={handleTargetAmountChange}
                        flex={1}
                        size="lg"
                        styles={{ input: { fontSize: '24px', fontWeight: 700 } }}
                      />
                    )}
                  />
                  <Controller
                    name="targetCurrency"
                    control={control}
                    render={({ field }) => (
                      <Select
                        data={CURRENCIES}
                        error={errors.targetCurrency?.message}
                        value={field.value}
                        onChange={(value) => handleTargetCurrencyChange(value as string)}
                      />
                    )}
                   />
                  <Text size="xs" c="dimmed">
                    Balance: {getBalance(targetCurrency).toFixed(2)} {targetCurrency}
                  </Text>
                  <Text size="xs" c="dimmed" opacity={conversion ? 1 : 0}>
                    {conversion ? `→ ${(getBalance(targetCurrency) + conversion.targetAmount).toFixed(2)} ${targetCurrency}` : '−'}
                  </Text>
                </Stack>
              </Group>

              <Text size="sm" c="dimmed" ta="center">
                1 {sourceCurrency} = {exchangeRate ?? '−'} {targetCurrency}
              </Text>

              <Group justify="flex-end" gap="xs">
                <Button variant="subtle" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!conversion || !!errors.sourceAmount || !!errors.targetAmount || !!errors.targetCurrency}
                >
                  Exchange
                </Button>
              </Group>
            </Stack>
          </form>
        )}

        {state.step === 'preview' && state.previewData && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">You are about to exchange:</Text>
            
            <Group gap="xs" align="baseline">
              <Text size="xl" fw={700}>
                {state.previewData.source_amount} {state.previewData.source_currency.toUpperCase()}
              </Text>
              <IconArrowRight size={20} />
              <Text size="xl" fw={700}>
                {state.previewData.target_amount} {state.previewData.target_currency.toUpperCase()}
              </Text>
            </Group>

            <Stack gap={2}>
              <Text size="sm" fw={500}>Exchange rate:</Text>
              <Text size="lg">1 {state.previewData.source_currency.toUpperCase()} = {state.previewData.rate} {state.previewData.target_currency.toUpperCase()}</Text>
            </Stack>

            <Stack gap={2}>
              <Text size="sm" fw={500}>Your balances will change:</Text>
              <Text size="sm" c="dimmed">
                {state.previewData.source_currency.toUpperCase()}: {getBalance(state.previewData.source_currency).toFixed(2)} → {(getBalance(state.previewData.source_currency) - parseFloat(state.previewData.source_amount)).toFixed(2)}
              </Text>
              <Text size="sm" c="dimmed">
                {state.previewData.target_currency.toUpperCase()}: {getBalance(state.previewData.target_currency).toFixed(2)} → {(getBalance(state.previewData.target_currency) + parseFloat(state.previewData.target_amount)).toFixed(2)}
              </Text>
            </Stack>

            {executeError && (
              <Alert color="red" title="Error">
                {executeError.message}
              </Alert>
            )}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={cancelPreview}>
                Back
              </Button>
              <Button onClick={() => executeExchange(inputMode)} loading={isExecuting}>
                Confirm Exchange
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {state.step === 'success' && state.previewData && (
        <PaymentSuccessModal
          opened
          onClose={closeSuccess}
          amount={parseFloat(state.previewData.source_amount)}
          currency={state.previewData.source_currency}
          exchangeAmount={parseFloat(state.previewData.target_amount)}
          exchangeCurrency={state.previewData.target_currency}
          balanceChanges={[
            {
              oldBalance: balancesBeforeExchange[state.previewData.source_currency]?.toFixed(2) ?? '0.00',
              newBalance: getBalance(state.previewData.source_currency).toFixed(2),
              currency: state.previewData.source_currency,
            },
            {
              oldBalance: balancesBeforeExchange[state.previewData.target_currency]?.toFixed(2) ?? '0.00',
              newBalance: getBalance(state.previewData.target_currency).toFixed(2),
              currency: state.previewData.target_currency,
            },
          ]}
          title="Exchange Successful!"
        />
      )}
    </>
  );
};

export const IconExchange = TablerIconExchange;
