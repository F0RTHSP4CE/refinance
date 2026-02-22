import { Button, Group, Modal, Stack, Text } from '@mantine/core';
import { IconArrowRight } from '@tabler/icons-react';
import confetti from 'canvas-confetti';
import { useCallback, useEffect, useRef } from 'react';

const CONFETTI_COLORS = ['#FFD700', '#FFA500', '#FF6347', '#00C851', '#2BBBAD', '#fff', '#AA66CC'];

const fireConfetti = () => {
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

type BalanceChange = {
  oldBalance: string;
  newBalance: string;
  currency: string;
};

export type PaymentSuccessModalProps = {
  opened: boolean;
  onClose: () => void;
  amount: number;
  currency: string;
  oldBalance?: string | null;
  newBalance?: string | null;
  title?: string;
  exchangeAmount?: number;
  exchangeCurrency?: string;
  balanceChanges?: BalanceChange[];
};

export const PaymentSuccessModal = ({
  opened,
  onClose,
  amount,
  currency,
  oldBalance,
  newBalance,
  title = 'Payment Successful!',
  exchangeAmount,
  exchangeCurrency,
  balanceChanges,
}: PaymentSuccessModalProps) => {
  const hasFiredRef = useRef(false);

  useEffect(() => {
    if (opened && !hasFiredRef.current) {
      hasFiredRef.current = true;
      fireConfetti();
    }
    if (!opened) {
      hasFiredRef.current = false;
    }
  }, [opened]);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  const isExchange = exchangeAmount !== undefined && exchangeCurrency !== undefined;

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={title}
      centered
      withCloseButton={false}
      closeOnClickOutside
      closeOnEscape
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Your {isExchange ? 'exchange' : 'transaction'} has been completed.
        </Text>
        {isExchange ? (
          <Group gap="xs" align="baseline">
            <Text size="lg" fw={700}>
              {amount} {currency.toUpperCase()}
            </Text>
            <IconArrowRight size={20} />
            <Text size="lg" fw={700}>
              {exchangeAmount} {exchangeCurrency.toUpperCase()}
            </Text>
          </Group>
        ) : (
          <Group gap="xs" align="baseline">
            <Text size="lg" fw={700}>
              {amount} {currency.toUpperCase()}
            </Text>
          </Group>
        )}
        {balanceChanges && balanceChanges.length > 0 ? (
          <Stack gap={4}>
            <Text size="xs" c="dimmed">
              Balances updated:
            </Text>
            {balanceChanges.map((change, index) => (
              <Group key={index} gap="xs" align="baseline">
                <Text size="md" td="line-through" c="dimmed">
                  {change.oldBalance} {change.currency.toUpperCase()}
                </Text>
                <Text size="md" fw={700}>
                  → {change.newBalance} {change.currency.toUpperCase()}
                </Text>
              </Group>
            ))}
          </Stack>
        ) : oldBalance !== undefined &&
          oldBalance !== null &&
          newBalance !== undefined &&
          newBalance !== null ? (
          <Stack gap={4}>
            <Text size="xs" c="dimmed">
              Balance updated:
            </Text>
            <Group gap="xs" align="baseline">
              <Text size="md" td="line-through" c="dimmed">
                {oldBalance} {currency.toUpperCase()}
              </Text>
              <Text size="md" fw={700}>
                → {newBalance} {currency.toUpperCase()}
              </Text>
            </Group>
          </Stack>
        ) : null}
        <Button onClick={handleClose} fullWidth>
          OK
        </Button>
      </Stack>
    </Modal>
  );
};
