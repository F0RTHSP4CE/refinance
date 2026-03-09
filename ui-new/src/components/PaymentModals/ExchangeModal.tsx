import { ActionIcon, Alert, Button, Group, NumberInput, Stack, Text } from '@mantine/core';
import {
  IconArrowDown,
  IconArrowRight,
  IconExchange as TablerIconExchange,
} from '@tabler/icons-react';
import { useState, useMemo } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/auth';
import { useExchangeFlow } from './useExchangeFlow';
import { getBalances } from '@/api/balance';
import { getExchangeRates } from '@/api/currency-exchange';
import { z } from 'zod';
import {
  AppModal,
  AppModalFooter,
  AppSelect,
  ModalStepHeader,
  SectionCard,
  StatCard,
} from '@/components/ui';

const CURRENCIES = [
  { value: 'GEL', label: 'GEL' },
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
] as const;

const exchangeSchema = z
  .object({
    sourceCurrency: z.enum(['GEL', 'USD', 'EUR']),
    targetCurrency: z.enum(['GEL', 'USD', 'EUR']),
    sourceAmount: z.number().min(0.01, 'Amount must be at least 0.01').optional(),
    targetAmount: z.number().min(0.01, 'Amount must be at least 0.01').optional(),
  })
  .refine((data) => data.sourceCurrency !== data.targetCurrency, {
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

  if (sourceAmount && !targetAmount) {
    return {
      sourceAmount,
      targetAmount: Math.floor(sourceAmount * conversionRate * 100) / 100,
      rate: Math.floor(conversionRate * 100) / 100,
    };
  } else if (targetAmount && !sourceAmount) {
    return {
      sourceAmount: Math.floor((targetAmount / conversionRate) * 100) / 100,
      targetAmount,
      rate: Math.floor(conversionRate * 100) / 100,
    };
  }
  return null;
}

export const ExchangeModal = ({ opened, onClose }: ExchangeModalProps) => {
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const {
    state,
    setPreviewData,
    executeExchange,
    cancelPreview,
    goToPreview,
    closeSuccess,
    reset,
    isExecuting,
    executeError,
  } = useExchangeFlow();

  const { data: freshBalances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: actorEntity !== null,
  });

  const { data: ratesData } = useQuery({
    queryKey: ['exchange-rates'],
    queryFn: () => getExchangeRates(),
    staleTime: Infinity,
  });

  const rates = useMemo(() => ratesData?.[0]?.currencies ?? [], [ratesData]);

  const [inputMode, setInputMode] = useState<'source' | 'target'>('source');
  const [balancesBeforeExchange, setBalancesBeforeExchange] = useState<Record<string, number>>({});

  const {
    control,
    setValue,
    formState: { errors },
  } = useForm<ExchangeFormValues>({
    resolver: zodResolver(exchangeSchema),
    defaultValues: {
      sourceCurrency: 'USD',
      targetCurrency: 'GEL',
      sourceAmount: undefined,
      targetAmount: undefined,
    },
  });

  const [sourceCurrency, targetCurrency, sourceAmount, targetAmount] = useWatch({
    control,
    name: ['sourceCurrency', 'targetCurrency', 'sourceAmount', 'targetAmount'],
  });

  const getBalance = (currency: string): number => {
    const key = currency.toLowerCase() as keyof NonNullable<typeof freshBalances>['completed'];
    return freshBalances?.completed?.[key] ? parseFloat(freshBalances.completed[key]) : 0;
  };

  const conversion = useMemo(() => {
    return calculateConversion(sourceAmount, targetAmount, sourceCurrency, targetCurrency, rates);
  }, [sourceAmount, targetAmount, sourceCurrency, targetCurrency, rates]);

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
    goToPreview();
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
    const currentSourceAmount = sourceAmount;
    const currentTargetAmount = targetAmount;

    setValue('sourceCurrency', targetCurrency);
    setValue('targetCurrency', sourceCurrency);

    if (currentSourceAmount && !currentTargetAmount) {
      setValue('sourceAmount', currentSourceAmount);
      setValue('targetAmount', undefined);
    } else if (currentTargetAmount && !currentSourceAmount) {
      setValue('targetAmount', currentTargetAmount);
      setValue('sourceAmount', undefined);
    } else {
      setValue('sourceAmount', undefined);
      setValue('targetAmount', undefined);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSuccessClose = () => {
    closeSuccess();
    onClose();
  };

  if (!actorEntity) return null;

  return (
    <AppModal
      opened={opened}
      onClose={state.step === 'success' ? handleSuccessClose : handleClose}
      variant="form"
      title={state.step === 'success' ? 'Exchange completed' : 'Exchange balance'}
      subtitle={
        state.step === 'success'
          ? 'The balance move has been applied and the updated balances are shown below.'
          : 'Convert between currencies with a quick review step before anything is executed.'
      }
      closeOnClickOutside={state.step === 'form'}
      closeOnEscape={state.step === 'form'}
      footer={
        state.step === 'form' ? (
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={handleClose}>
                Cancel
              </Button>
            }
            primary={
              <Button
                onClick={handleGoToPreview}
                disabled={
                  !conversion ||
                  !!errors.sourceAmount ||
                  !!errors.targetAmount ||
                  !!errors.targetCurrency
                }
              >
                Review exchange
              </Button>
            }
          />
        ) : state.step === 'preview' ? (
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={cancelPreview}>
                Back
              </Button>
            }
            primary={
              <Button onClick={() => executeExchange(inputMode)} loading={isExecuting}>
                Confirm exchange
              </Button>
            }
          />
        ) : (
          <AppModalFooter primary={<Button onClick={handleSuccessClose}>Close</Button>} />
        )
      }
    >
      <Stack gap="lg">
        {state.step === 'form' && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleGoToPreview();
            }}
          >
            <Stack gap="md">
              <ModalStepHeader
                eyebrow="Step 1"
                title="Set the currencies and amount"
                description="Enter the amount on either side and the exchange preview will calculate the other value."
              />

              <Group align="flex-start">
                <Stack gap={4} flex={1}>
                  <Text size="xs" c="dimmed" fw={600}>
                    From
                  </Text>
                  <Controller
                    name="sourceAmount"
                    control={control}
                    render={({ field }) => (
                      <NumberInput
                        aria-label="From amount"
                        placeholder="0.00"
                        min={0.01}
                        step={0.01}
                        decimalScale={2}
                        error={errors.sourceAmount?.message}
                        value={targetAmount && conversion ? conversion.sourceAmount : field.value}
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
                      <AppSelect
                        aria-label="From currency"
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
                    {conversion
                      ? `→ ${(getBalance(sourceCurrency) - conversion.sourceAmount).toFixed(2)} ${sourceCurrency}`
                      : '−'}
                  </Text>
                </Stack>

                <ActionIcon
                  variant="light"
                  size="lg"
                  onClick={swapCurrencies}
                  aria-label="Swap currencies"
                  mt={32}
                >
                  <IconArrowDown size={20} />
                </ActionIcon>

                <Stack gap={4} flex={1}>
                  <Text size="xs" c="dimmed" fw={600}>
                    To
                  </Text>
                  <Controller
                    name="targetAmount"
                    control={control}
                    render={({ field }) => (
                      <NumberInput
                        aria-label="To amount"
                        placeholder="0.00"
                        min={0.01}
                        step={0.01}
                        decimalScale={2}
                        error={errors.targetAmount?.message}
                        value={sourceAmount && conversion ? conversion.targetAmount : field.value}
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
                      <AppSelect
                        aria-label="To currency"
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
                    {conversion
                      ? `→ ${(getBalance(targetCurrency) + conversion.targetAmount).toFixed(2)} ${targetCurrency}`
                      : '−'}
                  </Text>
                </Stack>
              </Group>

              <Text size="sm" c="dimmed" ta="center">
                1 {sourceCurrency} = {exchangeRate ?? '−'} {targetCurrency}
              </Text>
            </Stack>
          </form>
        )}

        {state.step === 'preview' && state.previewData && (
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Step 2"
              title="Review exchange"
              description="Check the direction, rate, and resulting balances before confirming."
            />

            <SectionCard title="Exchange direction">
              <Group gap="xs" align="baseline">
                <Text size="xl" fw={700}>
                  {state.previewData.source_amount}{' '}
                  {state.previewData.source_currency.toUpperCase()}
                </Text>
                <IconArrowRight size={20} />
                <Text size="xl" fw={700}>
                  {state.previewData.target_amount}{' '}
                  {state.previewData.target_currency.toUpperCase()}
                </Text>
              </Group>
            </SectionCard>

            <SectionCard title="Rate">
              <Text size="lg">
                1 {state.previewData.source_currency.toUpperCase()} = {state.previewData.rate}{' '}
                {state.previewData.target_currency.toUpperCase()}
              </Text>
            </SectionCard>

            <SectionCard title="Balance impact">
              <Group grow align="stretch">
                <StatCard
                  label={state.previewData.source_currency.toUpperCase()}
                  value={(
                    getBalance(state.previewData.source_currency) -
                    parseFloat(state.previewData.source_amount)
                  ).toFixed(2)}
                  caption={`Was ${getBalance(state.previewData.source_currency).toFixed(2)}`}
                />
                <StatCard
                  label={state.previewData.target_currency.toUpperCase()}
                  value={(
                    getBalance(state.previewData.target_currency) +
                    parseFloat(state.previewData.target_amount)
                  ).toFixed(2)}
                  caption={`Was ${getBalance(state.previewData.target_currency).toFixed(2)}`}
                />
              </Group>
            </SectionCard>

            {executeError && (
              <Alert color="red" title="Error">
                {executeError.message}
              </Alert>
            )}
          </Stack>
        )}

        {state.step === 'success' && state.previewData ? (
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Completed"
              title="Balances updated"
              description="The exchange is complete and the new balances are reflected below."
            />

            <SectionCard title="Result">
              <Group gap="xs" align="baseline">
                <Text size="xl" fw={700}>
                  {state.previewData.source_amount}{' '}
                  {state.previewData.source_currency.toUpperCase()}
                </Text>
                <IconArrowRight size={20} />
                <Text size="xl" fw={700}>
                  {state.previewData.target_amount}{' '}
                  {state.previewData.target_currency.toUpperCase()}
                </Text>
              </Group>
            </SectionCard>

            <Group grow align="stretch">
              <StatCard
                label={`${state.previewData.source_currency.toUpperCase()} balance`}
                value={getBalance(state.previewData.source_currency).toFixed(2)}
                caption={`Was ${balancesBeforeExchange[state.previewData.source_currency]?.toFixed(2) ?? '0.00'}`}
              />
              <StatCard
                label={`${state.previewData.target_currency.toUpperCase()} balance`}
                value={getBalance(state.previewData.target_currency).toFixed(2)}
                caption={`Was ${balancesBeforeExchange[state.previewData.target_currency]?.toFixed(2) ?? '0.00'}`}
              />
            </Group>
          </Stack>
        ) : null}
      </Stack>
    </AppModal>
  );
};

export const IconExchange = TablerIconExchange;
