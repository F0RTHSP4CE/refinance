import { Button, Stack } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getTransactions } from '@/api/transactions';
import {
  transactionTableColumns,
  TransactionDetailsModal,
  useTransactionDetailsModal,
} from '@/components/Transactions';
import { DataTable, EmptyState, SectionCard, StatusBadge, TagList } from '@/components/ui';
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
    <SectionCard
      title="Recent movement"
      description="A short live feed of the latest money movement touching your F0RTHSP4CE account."
      action={
        <Button component={Link} to="/transactions" variant="subtle" size="sm">
          View all transactions
        </Button>
      }
    >
      <Stack gap="md">
        {transactions.length === 0 && !transactionsData ? (
          <EmptyState
            compact
            title="Loading transactions..."
            description="Recent activity will appear here in a moment."
          />
        ) : (
          <DataTable
            columns={transactionTableColumns}
            data={transactions}
            emptyMessage="No transactions."
            onRowClick={openTransaction}
            getRowAriaLabel={(transaction) => `Open transaction #${transaction.id}`}
            renderMobileTitle={(transaction) =>
              `${transaction.from_entity.name} -> ${transaction.to_entity.name}`
            }
            renderMobileSubtitle={(transaction) =>
              `${transaction.amount} ${transaction.currency.toUpperCase()}`
            }
            renderMobileAside={(transaction) => (
              <StatusBadge tone={transaction.status === 'completed' ? 'success' : 'draft'} size="sm">
                {transaction.status}
              </StatusBadge>
            )}
            renderMobileDetails={(transaction) => [
              { label: 'Comment', value: transaction.comment || '—' },
              { label: 'Actor', value: transaction.actor_entity.name },
              {
                label: 'Tags',
                value: transaction.tags.length ? <TagList tags={transaction.tags} /> : '—',
              },
            ]}
          />
        )}
        <TransactionDetailsModal
          opened={opened}
          transaction={selectedTransaction}
          onClose={closeTransaction}
        />
      </Stack>
    </SectionCard>
  );
};
