import { Alert, Button, Group, Modal, Select, Stack, Text } from '@mantine/core';
import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { payInvoice } from '@/api/invoices';
import type { Invoice, Transaction } from '@/types/api';

type InvoicePayModalProps = {
  opened: boolean;
  invoice: Invoice | null;
  onClose: () => void;
  onPaid?: (transaction: Transaction) => void;
};

export const InvoicePayModal = ({ opened, invoice, onClose, onPaid }: InvoicePayModalProps) => {
  const queryClient = useQueryClient();
  const options = useMemo(
    () =>
      (invoice?.amounts ?? []).map((entry) => ({
        value: entry.currency,
        label: `${entry.amount} ${entry.currency.toUpperCase()}`,
      })),
    [invoice?.amounts]
  );
  const [currency, setCurrency] = useState<string | null>(options[0]?.value ?? null);
  const selectedCurrency =
    currency && options.some((option) => option.value === currency)
      ? currency
      : (options[0]?.value ?? null);

  const payMutation = useMutation({
    mutationFn: async () => {
      if (!invoice || !selectedCurrency) {
        throw new Error('Select a currency to pay this invoice.');
      }

      return payInvoice({ invoice, currency: selectedCurrency });
    },
    onSuccess: async (transaction) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
        queryClient.invalidateQueries({ queryKey: ['invoice'] }),
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['fees'] }),
        queryClient.invalidateQueries({ queryKey: ['pendingInvoices'] }),
      ]);
      onPaid?.(transaction);
      onClose();
    },
  });

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={invoice ? `Pay Invoice #${invoice.id}` : 'Pay invoice'}
      centered
    >
      <Stack gap="md">
        {invoice ? (
          <>
            <Text size="sm" c="dimmed">
              Choose which invoice amount to pay. The payment is created as a completed transaction.
            </Text>
            <Select
              label="Amount"
              data={options}
              value={selectedCurrency}
              onChange={setCurrency}
              allowDeselect={false}
            />
          </>
        ) : null}

        {payMutation.isError ? (
          <Alert color="red" title="Payment failed">
            {payMutation.error.message}
          </Alert>
        ) : null}

        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={() => payMutation.mutate()}
            loading={payMutation.isPending}
          >
            Pay now
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
