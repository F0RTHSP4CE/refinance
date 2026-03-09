import { Alert, Button, Center, Group, Stack, Text, Tooltip } from '@mantine/core';
import { IconCopy } from '@tabler/icons-react';
import confetti from 'canvas-confetti';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { QRCodeSVG } from 'qrcode.react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getDeposit, getPaymentUrl } from '@/api/deposits';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';
import { formatRelativeTime } from '@/utils/formatRelativeTime';
import { POLLING_INTERVALS } from '@/constants/polling';
import {
  AppCard,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from '@/components/ui';

const CONFETTI_COLORS = ['#FFD700', '#FFA500', '#FF6347', '#00C851', '#2BBBAD', '#fff', '#AA66CC'];

const fireConfetti = () => {
  // --- Wave 1: center burst ---
  const burst = (ratio: number, opts: confetti.Options) =>
    confetti({
      particleCount: Math.floor(150 * ratio),
      origin: { y: 0.65 },
      colors: CONFETTI_COLORS,
      disableForReducedMotion: true,
      ...opts,
    });
  burst(0.3, { spread: 30, startVelocity: 55, decay: 0.94, scalar: 1.1 });
  burst(0.25, { spread: 60, startVelocity: 45, decay: 0.92 });
  burst(0.35, { spread: 100, decay: 0.91, scalar: 0.9 });

  // --- Wave 2: side cannons ---
  setTimeout(() => {
    confetti({
      particleCount: 40,
      angle: 60,
      spread: 50,
      origin: { x: 0, y: 0.65 },
      colors: CONFETTI_COLORS,
      startVelocity: 45,
      decay: 0.93,
    });
    confetti({
      particleCount: 40,
      angle: 120,
      spread: 50,
      origin: { x: 1, y: 0.65 },
      colors: CONFETTI_COLORS,
      startVelocity: 45,
      decay: 0.93,
    });
  }, 300);

  // --- Wave 3: gentle rain from top ---
  const rainEnd = Date.now() + 1200;
  const rainInterval = setInterval(() => {
    if (Date.now() > rainEnd) {
      clearInterval(rainInterval);
      return;
    }
    confetti({
      particleCount: 2,
      startVelocity: 0,
      origin: { x: Math.random(), y: -0.05 },
      colors: CONFETTI_COLORS,
      gravity: 0.6,
      scalar: 1.1,
      drift: (Math.random() - 0.5) * 0.4,
      ticks: 300,
    });
  }, 50);
};

// Validate deposit ID safely
const validateDepositId = (id: string | undefined): number | null => {
  if (!id) return null;
  const parsed = parseInt(id, 10);
  if (Number.isNaN(parsed) || parsed <= 0 || parsed > Number.MAX_SAFE_INTEGER) {
    return null;
  }
  return parsed;
};

export const DepositDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const depositId = useMemo(() => validateDepositId(id), [id]);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const successShownRef = useRef(false);

  const actorEntity = useAuthStore((state) => state.actorEntity);

  const {
    data: deposit,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['deposit', depositId],
    queryFn: ({ signal }) =>
      depositId ? getDeposit(depositId, signal) : Promise.reject(new Error('Invalid deposit ID')),
    enabled: depositId !== null,
    refetchInterval: POLLING_INTERVALS.DEPOSIT_STATUS,
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: !!actorEntity && deposit?.status === 'completed',
  });

  const paymentUrl = deposit ? getPaymentUrl(deposit) : null;

  // Handle successful deposit completion
  useEffect(() => {
    if (deposit?.status !== 'completed' || successShownRef.current) return;

    successShownRef.current = true;
    fireConfetti();

    if (actorEntity) {
      void queryClient.invalidateQueries({
        queryKey: ['balances', actorEntity.id],
      });
    }
  }, [deposit?.status, actorEntity, queryClient]);

  const oldBalance = useMemo(() => {
    if (deposit?.status !== 'completed' || !deposit || !balances) return null;

    const currency = deposit.currency.toLowerCase();
    const newVal = balances.completed?.[currency];
    if (newVal === undefined) {
      return '0.00';
    }

    const newNum = parseFloat(newVal);
    const added = parseFloat(String(deposit.amount));
    return (newNum - added).toFixed(2);
  }, [balances, deposit]);

  const handleCopy = useCallback(async () => {
    if (!paymentUrl) return;
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(paymentUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to copy to clipboard';
      setCopyError(message);
      setTimeout(() => setCopyError(null), 3000);
    }
  }, [paymentUrl]);

  const handleSuccessDone = useCallback(() => {
    navigate('/');
  }, [navigate]);

  if (depositId === null || isError) {
    return (
      <ErrorState
        title="Top-up link unavailable"
        description={error?.message ?? 'This top-up link is invalid or has already expired.'}
      />
    );
  }

  if (isLoading || !deposit) {
    return <LoadingState cards={1} lines={5} />;
  }

  const treasuryName = deposit.from_entity?.name ?? deposit.to_treasury?.name ?? 'keepz_in';

  const currency = deposit.currency.toLowerCase();
  const newBalanceStr = balances?.completed?.[currency];
  const newBalance = newBalanceStr ?? deposit.amount;
  const isCompleted = deposit.status === 'completed';
  const showSuccessPanel = isCompleted;

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="F0RTHSP4CE Finance"
        title={`${deposit.amount} ${deposit.currency.toUpperCase()} top-up`}
        subtitle="Keep this page open while the hosted payment settles, or use the link/QR code from another device."
        actions={
          <StatusBadge tone={isCompleted ? 'success' : 'warning'}>
            {deposit.status}
          </StatusBadge>
        }
      />

      {showSuccessPanel ? (
        <SectionCard
          title="Top-up complete"
          description="The payment landed and your balance is already updated."
          action={<Button onClick={handleSuccessDone}>Back home</Button>}
        >
          <Group gap="lg" wrap="wrap" align="end">
            <Stack gap={4}>
              <Text size="sm" className="app-muted-copy">
                Previous balance
              </Text>
              <Text size="lg" td="line-through" c="dimmed">
                {oldBalance ?? '—'} {deposit.currency.toUpperCase()}
              </Text>
            </Stack>
            <Stack gap={4}>
              <Text size="sm" className="app-muted-copy">
                Current balance
              </Text>
              <Text size="2rem" fw={800}>
                {newBalance} {deposit.currency.toUpperCase()}
              </Text>
            </Stack>
          </Group>
        </SectionCard>
      ) : null}

      <div className="app-page-grid lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
        <AppCard>
          <Stack gap="lg">
            <div>
              <Text size="xl" fw={700}>
                {deposit.amount} {deposit.currency.toUpperCase()}
              </Text>
              <Text size="sm" className="app-muted-copy">
                Provider: {deposit.provider} · Into fund {treasuryName}
              </Text>
            </div>

            {deposit.status === 'pending' && paymentUrl ? (
              <>
                <Group wrap="nowrap" gap="xs" h={42}>
                  <Button
                    component="a"
                    href={paymentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="default"
                    flex={1}
                    h="100%"
                    size="md"
                  >
                    Continue payment
                  </Button>
                  <Tooltip
                    label={copied ? 'Copied!' : 'Copy link'}
                    withArrow
                    opened={copied ? true : undefined}
                  >
                    <Button
                      variant="outline"
                      onClick={handleCopy}
                      h="100%"
                      w={42}
                      p={0}
                      style={{ flexShrink: 0 }}
                    >
                      <IconCopy size={18} />
                    </Button>
                  </Tooltip>
                </Group>

                {copyError ? (
                  <Alert color="red" variant="light" p="xs">
                    <Text size="xs">{copyError}</Text>
                  </Alert>
                ) : null}
              </>
            ) : (
              <Alert color={isCompleted ? 'green' : 'gray'} title={isCompleted ? 'Payment settled' : 'Waiting for payment'}>
                {isCompleted
                  ? 'The hosted payment finished and the resulting balance is shown above.'
                  : 'Open the payment link again if you still need to complete this top-up.'}
              </Alert>
            )}

            <Group gap="md" wrap="wrap">
              <Text size="xs" className="app-muted-copy">
                ID: {deposit.id}
              </Text>
              <Text size="xs" className="app-muted-copy">
                Created: {formatRelativeTime(deposit.created_at)}
              </Text>
            </Group>
          </Stack>
        </AppCard>

        <AppCard>
          <Stack gap="md" align="center">
            <Text fw={700}>Pay from another device</Text>
            <Text size="sm" ta="center" className="app-muted-copy">
              Scan this QR code from mobile if that is the fastest way to finish the top-up.
            </Text>
            {paymentUrl ? (
              <Center>
                <QRCodeSVG value={paymentUrl} size={200} level="M" />
              </Center>
            ) : (
              <Text size="sm" className="app-muted-copy">
                QR code appears when a payment link is available.
              </Text>
            )}
          </Stack>
        </AppCard>
      </div>
    </Stack>
  );
};
