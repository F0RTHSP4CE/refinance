import { Button, Group, Modal, Stack, Text } from '@mantine/core';

export type ConfirmTransactionModalProps = {
  opened: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  amount: number;
  currency: string;
  direction: 'pay' | 'receive';
  targetName: string;
};

export const ConfirmTransactionModal = ({
  opened,
  onConfirm,
  onCancel,
  isLoading,
  amount,
  currency,
  direction,
  targetName,
}: ConfirmTransactionModalProps) => {
  const message =
    direction === 'pay'
      ? `You are about to pay ${amount} ${currency.toUpperCase()} to ${targetName}.`
      : `You are about to receive ${amount} ${currency.toUpperCase()} from ${targetName}.`;

  return (
    <Modal
      opened={opened}
      onClose={onCancel}
      title="Confirm Transaction"
      centered
      closeOnClickOutside
      closeOnEscape
    >
      <Stack gap="md">
        <Text size="sm">{message}</Text>
        <Text size="xs" c="dimmed">
          This action cannot be undone.
        </Text>
        <Group justify="flex-end" gap="xs">
          <Button variant="subtle" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={onConfirm} loading={isLoading}>
            Confirm
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
