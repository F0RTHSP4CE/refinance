import { Button, SimpleGrid, Stack, TextInput } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { getEntities } from '@/api/entities';
import { getTags } from '@/api/tags';
import { getAllTransactions } from '@/api/transactions';
import {
  transactionTableColumns,
  TransactionDetailsModal,
  useTransactionDetailsModal,
} from '@/components/Transactions';
import {
  AppDateField,
  AppSelect,
  DataTable,
  ErrorState,
  FilterBar,
  PageHeader,
  RelativeDate,
  SectionCard,
  StatusBadge,
  TagList,
} from '@/components/ui';
import { APP_INPUT_CLASSNAMES, APP_INPUT_STYLES } from '@/components/ui/sharedInputStyles';
import { useAuthStore } from '@/stores/auth';

type TransactionFilterState = {
  search: string;
  status: 'all' | 'draft' | 'completed';
  currency: string;
  actorEntityId: string;
  relatedEntityId: string;
  tagId: string;
  fromDate: string;
  toDate: string;
};

const MAX_ITEMS = 500;

const DEFAULT_FILTERS: TransactionFilterState = {
  search: '',
  status: 'all',
  currency: '',
  actorEntityId: '',
  relatedEntityId: '',
  tagId: '',
  fromDate: '',
  toDate: '',
};

const matchesDateRange = (createdAt: string, fromDate: string, toDate: string) => {
  const transactionDate = createdAt.slice(0, 10);
  if (fromDate && transactionDate < fromDate) return false;
  if (toDate && transactionDate > toDate) return false;
  return true;
};

export const Transactions = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const { opened, selectedTransaction, openTransaction, closeTransaction } =
    useTransactionDetailsModal();
  const [filters, setFilters] = useState<TransactionFilterState>(DEFAULT_FILTERS);

  const transactionsQuery = useQuery({
    queryKey: ['transactionsPageAll', actorEntity?.id],
    queryFn: ({ signal }) => getAllTransactions({ signal }),
    enabled: actorEntity !== null,
  });

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'transactions-page'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
    enabled: actorEntity !== null,
  });

  const tagsQuery = useQuery({
    queryKey: ['tags', 'transactions-page'],
    queryFn: ({ signal }) => getTags({ limit: MAX_ITEMS, signal }),
    enabled: actorEntity !== null,
  });

  const transactions = useMemo(() => transactionsQuery.data ?? [], [transactionsQuery.data]);
  const entityOptions = useMemo(
    () =>
      (entitiesQuery.data?.items ?? [])
        .map((entity) => ({ value: String(entity.id), label: entity.name }))
        .sort((left, right) => left.label.localeCompare(right.label)),
    [entitiesQuery.data?.items]
  );
  const tagOptions = useMemo(
    () =>
      (tagsQuery.data?.items ?? [])
        .map((tag) => ({ value: String(tag.id), label: tag.name }))
        .sort((left, right) => left.label.localeCompare(right.label)),
    [tagsQuery.data?.items]
  );
  const currencyOptions = useMemo(() => {
    const currencies = new Set(transactions.map((transaction) => transaction.currency.toUpperCase()));
    return Array.from(currencies)
      .sort((left, right) => left.localeCompare(right))
      .map((currency) => ({ value: currency, label: currency }));
  }, [transactions]);

  const filteredTransactions = useMemo(() => {
    const search = filters.search.trim().toLowerCase();
    const relatedEntityId = filters.relatedEntityId ? Number(filters.relatedEntityId) : null;
    const actorEntityId = filters.actorEntityId ? Number(filters.actorEntityId) : null;
    const tagId = filters.tagId ? Number(filters.tagId) : null;

    return transactions.filter((transaction) => {
      if (filters.status !== 'all' && transaction.status !== filters.status) {
        return false;
      }
      if (filters.currency && transaction.currency.toUpperCase() !== filters.currency) {
        return false;
      }
      if (actorEntityId != null && transaction.actor_entity_id !== actorEntityId) {
        return false;
      }
      if (
        relatedEntityId != null &&
        transaction.from_entity_id !== relatedEntityId &&
        transaction.to_entity_id !== relatedEntityId
      ) {
        return false;
      }
      if (tagId != null && !transaction.tags.some((tag) => tag.id === tagId)) {
        return false;
      }
      if (!matchesDateRange(transaction.created_at, filters.fromDate, filters.toDate)) {
        return false;
      }
      if (!search) {
        return true;
      }

      const searchHaystack = [
        transaction.from_entity.name,
        transaction.to_entity.name,
        transaction.actor_entity.name,
        transaction.comment ?? '',
        ...transaction.tags.map((tag) => tag.name),
      ]
        .join(' ')
        .toLowerCase();

      return searchHaystack.includes(search);
    });
  }, [filters, transactions]);

  const activeFilterCount = Object.values(filters).filter(Boolean).length - (filters.status === 'all' ? 1 : 0);
  const resultSummary = `${filteredTransactions.length} of ${transactions.length} transaction${
    transactions.length === 1 ? '' : 's'
  } visible`;

  if (!actorEntity) {
    return null;
  }

  if (transactionsQuery.isError) {
    return (
      <ErrorState
        title="Transactions could not be loaded"
        description={transactionsQuery.error.message}
        onRetry={() => void transactionsQuery.refetch()}
      />
    );
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="F0RTHSP4CE movement"
        title="Transactions"
        subtitle="Filter transactions by who created them, who they involve, label, currency, status, or date without losing readability on smaller screens."
      />

      <FilterBar
        tone="accent"
        title="Filter transactions"
        description="Filter transactions by who created them, who they involve, label, currency, status, or date."
        resultSummary={resultSummary}
        action={
          activeFilterCount > 0 ? (
            <Button variant="subtle" onClick={() => setFilters(DEFAULT_FILTERS)}>
              Reset filters
            </Button>
          ) : null
        }
      >
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
            <TextInput
              label="Search"
              placeholder="Comment, member, entity, or label"
              size="md"
              radius="md"
              styles={APP_INPUT_STYLES}
              classNames={APP_INPUT_CLASSNAMES}
              value={filters.search}
              onChange={(event) =>
                setFilters((current) => ({ ...current, search: event.currentTarget.value }))
              }
            />
            <AppSelect
              label="Status"
              allowDeselect={false}
              data={[
                { value: 'all', label: 'All statuses' },
                { value: 'draft', label: 'Draft' },
                { value: 'completed', label: 'Completed' },
              ]}
              value={filters.status}
              onChange={(value) =>
                setFilters((current) => ({
                  ...current,
                  status: (value as TransactionFilterState['status']) || 'all',
                }))
              }
            />
            <AppSelect
              label="Currency"
              searchable
              clearable
              data={currencyOptions}
              value={filters.currency || null}
              onChange={(value) =>
                setFilters((current) => ({ ...current, currency: value ?? '' }))
              }
            />
            <AppSelect
              label="Created by"
              searchable
              clearable
              data={entityOptions}
              value={filters.actorEntityId || null}
              onChange={(value) =>
                setFilters((current) => ({ ...current, actorEntityId: value ?? '' }))
              }
              nothingFoundMessage={
                entitiesQuery.isLoading ? 'Loading entities...' : 'No entities found'
              }
            />
            <AppSelect
              label="Involves"
              searchable
              clearable
              data={entityOptions}
              value={filters.relatedEntityId || null}
              onChange={(value) =>
                setFilters((current) => ({ ...current, relatedEntityId: value ?? '' }))
              }
              nothingFoundMessage={
                entitiesQuery.isLoading ? 'Loading entities...' : 'No entities found'
              }
            />
            <AppSelect
              label="Label"
              searchable
              clearable
              data={tagOptions}
              value={filters.tagId || null}
              onChange={(value) =>
                setFilters((current) => ({ ...current, tagId: value ?? '' }))
              }
              nothingFoundMessage={tagsQuery.isLoading ? 'Loading labels...' : 'No labels found'}
            />
            <AppDateField
              label="From"
              value={filters.fromDate}
              onChange={(value) => setFilters((current) => ({ ...current, fromDate: value }))}
            />
            <AppDateField
              label="To"
              value={filters.toDate}
              onChange={(value) => setFilters((current) => ({ ...current, toDate: value }))}
            />
          </SimpleGrid>
        </Stack>
      </FilterBar>

      <SectionCard
        title="Transactions"
        description="Desktop keeps the full table. Mobile collapses each transaction into a readable card with the key context kept visible."
      >
        <DataTable
          columns={transactionTableColumns}
          data={filteredTransactions}
          isLoading={transactionsQuery.isLoading}
          loadingState={{ cards: 2, lines: 4 }}
          emptyState={{
            title: 'No matching transactions',
            description:
              'Try widening the filter window or clearing one of the entity, label, or status filters.',
          }}
          resultSummary={resultSummary}
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
            { label: 'Created', value: <RelativeDate isoString={transaction.created_at} /> },
            { label: 'Actor', value: transaction.actor_entity.name },
            { label: 'Comment', value: transaction.comment || '—' },
            {
              label: 'Labels',
              value: transaction.tags.length ? <TagList tags={transaction.tags} /> : '—',
            },
          ]}
        />
      </SectionCard>

      <TransactionDetailsModal
        opened={opened}
        transaction={selectedTransaction}
        onClose={closeTransaction}
      />
    </Stack>
  );
};
