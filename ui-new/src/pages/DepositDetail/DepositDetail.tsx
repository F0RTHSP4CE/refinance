import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { IconCopy } from '@tabler/icons-react';
import confetti from 'canvas-confetti';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { QRCodeSVG } from 'qrcode.react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  completeDepositDev,
  getDeposit,
  getPaymentUrl,
  isDevModeDeposit,
} from '@/api/deposits';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';
import { formatRelativeTime } from '@/utils/formatRelativeTime';
import { POLLING_INTERVALS } from '@/constants/polling';

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
  const [successOpen, setSuccessOpen] = useState(false);
  const [oldBalance, setOldBalance] = useState<string | null>(null);
  const [devCompleteError, setDevCompleteError] = useState<string | null>(null);
  const [devCompleteLoading, setDevCompleteLoading] = useState(false);
  
  // Use reducer pattern for complex state management instead of multiple refs
  const devCompleteState = useRef<{
    triggered: boolean;
    inFlight: boolean;
    successShown: boolean;
  }>({ triggered: false, inFlight: false, successShown: false });

  const actorEntity = useAuthStore((state) => state.actorEntity);

  const { data: deposit, isLoading, isError, error } = useQuery({
    queryKey: ['deposit', depositId],
    queryFn: ({ signal }) => depositId ? getDeposit(depositId, signal) : Promise.reject(new Error('Invalid deposit ID')),
    enabled: depositId !== null,
    refetchInterval: POLLING_INTERVALS.DEPOSIT_STATUS,
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: !!actorEntity && successOpen,
  });

  const paymentUrl = deposit ? getPaymentUrl(deposit) : null;
  const isDevDeposit = deposit ? isDevModeDeposit(deposit) : false;

  const handleCompleteDev = useCallback(async () => {
    if (!deposit || devCompleteState.current.inFlight) return;
    devCompleteState.current.inFlight = true;
    setDevCompleteError(null);
    setDevCompleteLoading(true);
    try {
      await completeDepositDev(deposit.id);
      await queryClient.invalidateQueries({ queryKey: ['deposit', depositId] });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to complete deposit';
      setDevCompleteError(message);
      // Reset state to allow retry
      devCompleteState.current.triggered = false;
    } finally {
      setDevCompleteLoading(false);
      devCompleteState.current.inFlight = false;
    }
  }, [deposit, depositId, queryClient]);

  // Auto-complete dev deposits after delay
  useEffect(() => {
    if (
      !isDevDeposit ||
      !deposit ||
      deposit.status !== 'pending' ||
      devCompleteState.current.triggered ||
      devCompleteState.current.inFlight
    ) {
      return;
    }
    
    devCompleteState.current.triggered = true;
    const timer = setTimeout(() => {
      void handleCompleteDev();
    }, 10_000);
    
    return () => clearTimeout(timer);
  }, [isDevDeposit, deposit, handleCompleteDev]);

  // Handle successful deposit completion
  useEffect(() => {
    if (deposit?.status !== 'completed' || devCompleteState.current.successShown) return;
    
    devCompleteState.current.successShown = true;
    fireConfetti();
    setSuccessOpen(true);
    
    if (actorEntity) {
      void queryClient.invalidateQueries({
        queryKey: ['balances', actorEntity.id],
      });
    }
  }, [deposit?.status, actorEntity, queryClient]);

  useEffect(() => {
    if (!successOpen || !deposit || !balances) return;
    const currency = deposit.currency.toLowerCase();
    const newVal = balances.completed?.[currency];
    if (newVal !== undefined) {
      const newNum = parseFloat(newVal);
      const added = parseFloat(String(deposit.amount));
      setOldBalance((newNum - added).toFixed(2));
    } else {
      setOldBalance('0.00');
    }
  }, [successOpen, deposit, balances]);

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

  const handleSuccessOk = useCallback(() => {
    setSuccessOpen(false);
    navigate('/');
  }, [navigate]);

  if (depositId === null || isError) {
    return (
      <Center h="100%">
        <Text c="dimmed">{error?.message ?? 'Invalid deposit ID'}</Text>
      </Center>
    );
  }

  if (isLoading || !deposit) {
    return (
      <Center h="100%">
        <Loader />
      </Center>
    );
  }

  const treasuryName =
    deposit.from_entity?.name ?? deposit.to_treasury?.name ?? 'keepz_in';

  const currency = deposit.currency.toLowerCase();
  const newBalanceStr = balances?.completed?.[currency];
  const newBalance = newBalanceStr ?? deposit.amount;

  return (
    <>
      <Center py="xl">
        <Card shadow="sm" padding="lg" radius="md" w="100%" maw={420}>
          <Stack gap="lg">
            <div>
              <Text size="xl" fw={700}>
                {deposit.amount} {deposit.currency.toUpperCase()}
              </Text>
              <Text size="sm" c="dimmed">
                Status: {deposit.status} · Provider: {deposit.provider}
              </Text>
            </div>

            {deposit.status === 'pending' && paymentUrl && (
              <>
                <Group wrap="nowrap" gap="xs" h={36}>
                  <Button
                    component="a"
                    href={paymentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="filled"
                    flex={1}
                    h="100%"
                    size="md"
                  >
                    Pay now
                  </Button>
                  <Tooltip
                    label={copied ? 'Copied!' : 'Copy link'}
                    withArrow
                    opened={copied ? true : undefined}
                  >
                    <Button
                      variant="filled"
                      onClick={handleCopy}
                      h="100%"
                      w={36}
                      p={0}
                      style={{ flexShrink: 0 }}
                    >
                      <IconCopy size={18} />
                    </Button>
                  </Tooltip>
                </Group>

                {copyError && (
                  <Alert color="red" variant="light" p="xs">
                    <Text size="xs">{copyError}</Text>
                  </Alert>
                )}

                {isDevDeposit && (
                  <>
                    <Text size="xs" c="dimmed">
                      Dev mode: deposit will auto-complete in ~10 seconds.
                    </Text>
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => {
                        devCompleteState.current.triggered = true;
                        void handleCompleteDev();
                      }}
                      loading={devCompleteLoading}
                    >
                      Complete now (dev)
                    </Button>
                  </>
                )}

                {devCompleteError && (
                  <Alert color="gray" title="Dev complete failed">
                    <Stack gap="xs">
                      <Text size="sm">{devCompleteError}</Text>
                      <Button
                        variant="subtle"
                        size="xs"
                        w="fit-content"
                        onClick={() => void handleCompleteDev()}
                        loading={devCompleteLoading}
                      >
                        Retry
                      </Button>
                    </Stack>
                  </Alert>
                )}

                <Text size="xs" c="dimmed">
                  Scan the QR code to pay from mobile.
                </Text>

                <Center>
                  <QRCodeSVG value={paymentUrl} size={200} level="M" />
                </Center>
              </>
            )}

            <Text size="sm" c="dimmed">
              Depositing to treasury {treasuryName}
            </Text>

            <Group gap="md">
              <Text size="xs" c="dimmed">
                ID: {deposit.id}
              </Text>
              <Text size="xs" c="dimmed">
                Created: {formatRelativeTime(deposit.created_at)}
              </Text>
            </Group>
          </Stack>
        </Card>
      </Center>

      <Modal
        opened={successOpen}
        onClose={handleSuccessOk}
        title="Payment successful!"
        centered
        withCloseButton={false}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Your balance has been updated.
          </Text>
          <Group gap="xs" align="baseline">
            {oldBalance !== null && (
              <Text size="lg" td="line-through" c="dimmed">
                {oldBalance} {deposit.currency.toUpperCase()}
              </Text>
            )}
            <Text size="lg" fw={700}>
              {newBalance} {deposit.currency.toUpperCase()}
            </Text>
          </Group>
          <Button onClick={handleSuccessOk} fullWidth>
            OK
          </Button>
        </Stack>
      </Modal>
    </>
  );
};
