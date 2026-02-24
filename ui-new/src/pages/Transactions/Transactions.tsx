import { Card, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { getAllTransactions } from '@/api/transactions';
import {
  transactionTableColumns,
  TransactionDetailsModal,
  useTransactionDetailsModal,
} from '@/components/Transactions';
import { DataTable } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';

export const Transactions = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const { opened, selectedTransaction, openTransaction, closeTransaction } =
    useTransactionDetailsModal();

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ['transactionsPageAll', actorEntity?.id],
    queryFn: ({ signal }) => getAllTransactions({ signal }),
    enabled: actorEntity !== null,
  });

  if (!actorEntity) {
    return (
      <Stack gap="md">
        <Text c="dimmed">Loading transactions...</Text>
      </Stack>
    );
  }

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Text size="lg" fw={700}>
          Transactions
        </Text>
        <DataTable
          columns={transactionTableColumns}
          data={transactions}
          emptyMessage={isLoading ? 'Loading transactions...' : 'No transactions.'}
          onRowClick={openTransaction}
          getRowAriaLabel={(transaction) => `Open transaction #${transaction.id}`}
        />
        <TransactionDetailsModal
          opened={opened}
          transaction={selectedTransaction}
          onClose={closeTransaction}
        />
      </Stack>
    </Card>
  );
};
