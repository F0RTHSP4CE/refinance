import { Button, Card, Group, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getTransactions } from '@/api/transactions';
import {
  transactionTableColumns,
  TransactionDetailsModal,
  useTransactionDetailsModal,
} from '@/components/Transactions';
import { DataTable } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';

const LIMIT = 10;

export const HomeTransactionsTableSection = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const { opened, selectedTransaction, openTransaction, closeTransaction } =
    useTransactionDetailsModal();

  const { data: transactionsData } = useQuery({
    queryKey: ['homeTransactionsTable', actorEntity?.id, LIMIT],
    queryFn: ({ signal }) =>
      getTransactions({
        entity_id: actorEntity!.id,
        limit: LIMIT,
        signal,
      }),
    enabled: actorEntity !== null,
  });

  const transactions = transactionsData?.items ?? [];

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Text size="lg" fw={700}>
            Latest Transactions
          </Text>
          <Button component={Link} to="/transactions" variant="light" size="sm">
            View all
          </Button>
        </Group>
        <DataTable
          columns={transactionTableColumns}
          data={transactions}
          emptyMessage="No transactions."
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
