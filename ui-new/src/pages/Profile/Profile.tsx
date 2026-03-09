import { Anchor, Button, Group, Stack, Text, Tooltip } from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getBalances } from '@/api/balance';
import { getEntity, getMe } from '@/api/entities';
import { getInvoices } from '@/api/invoices';
import { getTransactions } from '@/api/transactions';
import { InvoiceDetailsModal } from '@/components/Invoices/InvoiceDetailsModal';
import { MoneyActionModal } from '@/components/MoneyActionModal/MoneyActionModal';
import { TelegramAuthButton } from '@/components/TelegramAuth';
import {
  transactionTableColumns,
  TransactionDetailsModal,
  useTransactionDetailsModal,
} from '@/components/Transactions';
import {
  AmountsCurrency,
  AccentSurface,
  AppCard,
  AppTabs,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  RelativeDate,
  SectionCard,
  StatusBadge,
  TagList,
  type DataTableColumn,
} from '@/components/ui';
import { useTelegramAuthConfig } from '@/hooks/useTelegramAuthConfig';
import { ProfileStatistics } from './ProfileStatistics';
import { useAuthStore } from '@/stores/auth';
import type { Entity, Invoice } from '@/types/api';

const LIMIT = 20;

// Safely validate and parse entity ID from URL
const validateEntityId = (id: string | undefined): number | null => {
  if (!id) return null;
  const parsed = parseInt(id, 10);
  if (Number.isNaN(parsed) || parsed <= 0 || parsed > Number.MAX_SAFE_INTEGER) {
    return null;
  }
  return parsed;
};

export const Profile = () => {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const queryClient = useQueryClient();
  const telegramConfigQuery = useTelegramAuthConfig();

  const tab = searchParams.get('tab') ?? 'profile';
  const { opened, selectedTransaction, openTransaction, closeTransaction } =
    useTransactionDetailsModal();

  const validatedId = useMemo(() => validateEntityId(id), [id]);
  const profileId = id === undefined ? actorEntity?.id : validatedId;
  const isOwnProfile = profileId != null && profileId === actorEntity?.id;
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [moneyActionMode, setMoneyActionMode] = useState<'transfer' | 'request' | null>(null);

  useEffect(() => {
    if (!id && actorEntity) {
      navigate(`/profile/${actorEntity.id}`, { replace: true });
    }
  }, [id, actorEntity, navigate]);

  const {
    data: entity,
    isError: entityError,
    isLoading: entityLoading,
  } = useQuery({
    queryKey: ['entities', profileId],
    queryFn: ({ signal }) => {
      if (isOwnProfile) {
        return getMe(signal);
      }
      if (profileId) {
        return getEntity(profileId, signal);
      }
      return Promise.reject(new Error('Invalid profile ID'));
    },
    enabled: !!profileId,
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', profileId],
    queryFn: ({ signal }) => (profileId ? getBalances(profileId, signal) : null),
    enabled: !!profileId,
  });

  const { data: transactionsData } = useQuery({
    queryKey: ['transactions', profileId],
    queryFn: ({ signal }) =>
      profileId ? getTransactions({ entity_id: profileId, limit: LIMIT, signal }) : null,
    enabled: !!profileId,
  });

  const { data: invoicesData } = useQuery({
    queryKey: ['invoices', profileId],
    queryFn: ({ signal }) =>
      profileId ? getInvoices({ entity_id: profileId, limit: LIMIT, signal }) : null,
    enabled: !!profileId,
  });

  const currencies = useMemo(() => {
    if (!balances) return [];
    const allCurrencies = new Set([
      ...Object.keys(balances.completed || {}),
      ...Object.keys(balances.draft || {}),
    ]);
    return Array.from(allCurrencies);
  }, [balances]);

  const transactions = transactionsData?.items ?? [];
  const invoices = invoicesData?.items ?? [];
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const copyToClipboard = useCallback(async (text: string) => {
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to copy to clipboard';
      setCopyError(message);
      setTimeout(() => setCopyError(null), 3000);
    }
  }, []);

  if (!actorEntity) {
    return <LoadingState cards={1} lines={4} />;
  }

  if (profileId == null) {
    return (
      <ErrorState
        title="Profile not found"
        description={id ? 'This profile no longer exists or the link is invalid.' : 'Loading profile...'}
      />
    );
  }

  if (entityError || (profileId && !entity && !entityLoading)) {
    return (
      <ErrorState
        title="Profile not found"
        description="This profile could not be loaded. It may have been removed or you may not have access."
      />
    );
  }

  if (entityLoading || !entity) {
    return <LoadingState cards={2} lines={4} />;
  }

  const profileEntity = entity as Entity;

  const EntityLink = ({ entityRef }: { entityRef: { id: number; name: string } }) => (
    <Anchor size="sm" component={Link} to={`/profile/${entityRef.id}`} underline="hover" inherit>
      {entityRef.name}
    </Anchor>
  );

  const invoiceColumns: DataTableColumn<Invoice>[] = [
    { key: 'id', label: 'ID', render: (r) => <Text size="sm">{r.id}</Text> },
    {
      key: 'created_at',
      label: 'Date',
      render: (r) => <RelativeDate isoString={r.created_at} />,
    },
    {
      key: 'billing_period',
      label: 'Billing period',
      render: (r) => <Text size="sm">{(r.billing_period ?? '').slice(0, 7)}</Text>,
    },
    {
      key: 'from_entity',
      label: 'From',
      render: (r) => (
        <Group gap={6} wrap="wrap">
          <EntityLink entityRef={r.from_entity} />
          {r.from_entity.tags?.length ? <TagList tags={r.from_entity.tags} /> : null}
        </Group>
      ),
    },
    {
      key: 'to_entity',
      label: 'To',
      render: (r) => (
        <Group gap={6} wrap="wrap">
          <EntityLink entityRef={r.to_entity} />
          {r.to_entity.tags?.length ? <TagList tags={r.to_entity.tags} /> : null}
        </Group>
      ),
    },
    {
      key: 'amounts',
      label: 'Amounts',
      render: (r) => <AmountsCurrency amounts={r.amounts} />,
    },
    { key: 'comment', label: 'Comment', render: (r) => <Text size="sm">{r.comment || '—'}</Text> },
    {
      key: 'status',
      label: 'Status',
      render: (r) => (
        <StatusBadge
          tone={r.status === 'paid' ? 'success' : r.status === 'cancelled' ? 'danger' : 'warning'}
          size="sm"
        >
          {r.status}
        </StatusBadge>
      ),
    },
    {
      key: 'tags',
      label: 'Tags',
      render: (r) => (r.tags.length ? <TagList tags={r.tags} /> : <Text size="sm">—</Text>),
    },
    {
      key: 'actor_entity',
      label: 'Actor',
      render: (r) => <EntityLink entityRef={r.actor_entity} />,
    },
  ];

  const e = profileEntity;

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow={isOwnProfile ? 'Your finance profile' : 'Member profile'}
        title={e.name}
        subtitle={
          isOwnProfile
            ? 'Manage linked auth, inspect balances, and review your latest F0RTHSP4CE activity from one place.'
            : 'Review balance, dues history, and recent movement without dropping into a dense admin screen.'
        }
        actions={
          !isOwnProfile ? (
            <Group gap="xs">
              <Button variant="default" size="sm" onClick={() => setMoneyActionMode('transfer')}>
                Transfer
              </Button>
              <Button variant="outline" size="sm" onClick={() => setMoneyActionMode('request')}>
                Request
              </Button>
            </Group>
          ) : undefined
        }
      />

      <AppTabs
        value={tab}
        onChange={(value) =>
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.set('tab', value ?? 'profile');
            return next;
          })
        }
      >
        <AppTabs.List>
          <AppTabs.Tab value="profile">Overview</AppTabs.Tab>
          <AppTabs.Tab value="statistics">Stats</AppTabs.Tab>
        </AppTabs.List>

        <AppTabs.Panel value="profile">
          <Stack gap="lg" mt="md">
            <AccentSurface>
              <Stack gap="md">
                <Group justify="space-between" align="start" wrap="wrap">
                  <Group gap="xs" wrap="wrap">
                    {isOwnProfile ? <StatusBadge tone="info">This is you</StatusBadge> : null}
                    <StatusBadge size="sm" tone={e.active ? 'success' : 'danger'}>
                      {e.active ? 'Active' : 'Inactive'}
                    </StatusBadge>
                  </Group>
                </Group>
                <Group gap="md">
                  <Text size="sm" c="dimmed">
                    ID: {e.id}
                  </Text>
                  <Text size="sm" c="dimmed">
                    Name: {e.name}
                  </Text>
                </Group>
                {e?.tags?.length ? <TagList tags={e.tags} showAll /> : null}
                {e?.created_at && (
                  <Text size="sm" c="dimmed" component="span">
                    Created: <RelativeDate isoString={e.created_at} />
                  </Text>
                )}

                {isOwnProfile && (e?.auth?.telegram_id || e?.auth?.signal_id) && (
                  <>
                    <Group gap="md" mt="xs">
                      {e.auth.telegram_id != null && String(e.auth.telegram_id).trim() && (
                        <Tooltip label={copied ? 'Copied!' : 'Click to copy'}>
                          <Text size="sm" c="dimmed">
                            Telegram:{' '}
                            <Text
                              component="span"
                              size="sm"
                              c="dimmed"
                              className="cursor-pointer border-b border-dashed border-[var(--mantine-color-dimmed)]"
                              onClick={() => copyToClipboard(String(e.auth!.telegram_id))}
                            >
                              {String(e.auth.telegram_id)}
                            </Text>
                          </Text>
                        </Tooltip>
                      )}
                      {e.auth.signal_id != null && String(e.auth.signal_id).trim() && (
                        <Tooltip label={copied ? 'Copied!' : 'Click to copy'}>
                          <Text size="sm" c="dimmed">
                            Signal:{' '}
                            <Text
                              component="span"
                              size="sm"
                              c="dimmed"
                              className="cursor-pointer border-b border-dashed border-[var(--mantine-color-dimmed)]"
                              onClick={() => copyToClipboard(String(e.auth!.signal_id))}
                            >
                              {String(e.auth.signal_id)}
                            </Text>
                          </Text>
                        </Tooltip>
                      )}
                    </Group>
                    {copyError ? (
                      <Text size="xs" c="red" mt={4}>
                        {copyError}
                      </Text>
                    ) : null}
                  </>
                )}

                {isOwnProfile ? (
                  <AppCard p="md">
                    <Stack gap="sm">
                      <Text fw={600}>Telegram access</Text>
                      <Text size="sm" c="dimmed">
                        Link Telegram once to unlock the fastest sign-in path back into
                        F0RTHSP4CE Finance.
                      </Text>
                      <TelegramAuthButton
                        mode="connect"
                        botUsername={telegramConfigQuery.data?.bot_username}
                        enabled={telegramConfigQuery.data?.enabled}
                        reason={telegramConfigQuery.data?.reason}
                        loading={telegramConfigQuery.isLoading}
                        onSuccess={() => {
                          void queryClient.invalidateQueries({ queryKey: ['entities', profileId] });
                        }}
                      />
                    </Stack>
                  </AppCard>
                ) : null}
              </Stack>
            </AccentSurface>

            <SectionCard
              title="Balances"
              description="Available and draft amounts for this profile."
            >
              {balances && currencies.length > 0 ? (
                <Stack gap="xs">
                  {currencies.map((currency: string) => {
                    const completed = balances.completed?.[currency] ?? '0';
                    const draft = balances.draft?.[currency];
                    const hasDraft = draft && parseFloat(draft) !== 0;
                    return (
                      <Group key={currency} gap="xs">
                        <Text size="sm" fw={500}>
                          {completed} {currency.toUpperCase()}
                        </Text>
                        {hasDraft && (
                          <Text size="xs" c="dimmed">
                            ({parseFloat(draft) > 0 ? '+' : ''}
                            {draft} draft)
                          </Text>
                        )}
                      </Group>
                    );
                  })}
                </Stack>
              ) : (
                <EmptyState
                  compact
                  title="No balance yet"
                  description="This profile has not moved any money through the space yet."
                />
              )}
            </SectionCard>

            <SectionCard
              title="Recent movement"
              description="Recent money movement for this profile."
            >
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
                  <StatusBadge
                    tone={transaction.status === 'completed' ? 'success' : 'draft'}
                    size="sm"
                  >
                    {transaction.status}
                  </StatusBadge>
                )}
                renderMobileDetails={(transaction) => [
                  { label: 'Actor', value: transaction.actor_entity.name },
                  { label: 'Comment', value: transaction.comment || '—' },
                  {
                    label: 'Tags',
                    value: transaction.tags.length ? <TagList tags={transaction.tags} /> : '—',
                  },
                ]}
              />
              <TransactionDetailsModal
                opened={opened}
                transaction={selectedTransaction}
                onClose={closeTransaction}
              />
            </SectionCard>

            <SectionCard
              title="Dues & invoices"
              description="The latest dues and invoice records tied to this profile."
            >
              <DataTable
                columns={invoiceColumns}
                data={invoices}
                emptyMessage="No invoices."
                onRowClick={(invoice) => setSelectedInvoice(invoice)}
                getRowAriaLabel={(invoice) => `Open invoice #${invoice.id}`}
                renderMobileTitle={(invoice) => `Invoice #${invoice.id}`}
                renderMobileSubtitle={(invoice) =>
                  invoice.amounts.map((item) => `${item.amount} ${item.currency.toUpperCase()}`).join(' · ')
                }
                renderMobileAside={(invoice) => (
                  <StatusBadge
                    tone={
                      invoice.status === 'paid'
                        ? 'success'
                        : invoice.status === 'cancelled'
                          ? 'danger'
                          : 'warning'
                    }
                    size="sm"
                  >
                    {invoice.status}
                  </StatusBadge>
                )}
                renderMobileDetails={(invoice) => [
                  { label: 'Billing period', value: (invoice.billing_period ?? '').slice(0, 7) || '—' },
                  { label: 'From', value: invoice.from_entity.name },
                  { label: 'To', value: invoice.to_entity.name },
                  {
                    label: 'Tags',
                    value: invoice.tags.length ? <TagList tags={invoice.tags} /> : '—',
                  },
                ]}
              />
            </SectionCard>
          </Stack>
        </AppTabs.Panel>

        <AppTabs.Panel value="statistics">
          {profileId != null && <ProfileStatistics profileId={profileId} />}
        </AppTabs.Panel>
      </AppTabs>

      <InvoiceDetailsModal
        opened={selectedInvoice != null}
        invoice={selectedInvoice}
        onClose={() => setSelectedInvoice(null)}
      />

      <MoneyActionModal
        opened={moneyActionMode != null}
        mode={moneyActionMode ?? 'transfer'}
        onClose={() => setMoneyActionMode(null)}
        initialFromEntityId={moneyActionMode === 'transfer' ? actorEntity?.id : e.id}
        initialToEntityId={moneyActionMode === 'request' ? actorEntity?.id : e.id}
        title={
          moneyActionMode
            ? moneyActionMode === 'transfer'
              ? `Transfer with ${e.name}`
              : `Request from ${e.name}`
            : undefined
        }
      />
    </Stack>
  );
};
