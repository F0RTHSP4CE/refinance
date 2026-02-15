import { Anchor, Badge, Flex, Group, Stack, Tabs, Text, Tooltip } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getBalances } from '@/api/balance';
import { getEntity, getMe } from '@/api/entities';
import { getInvoices } from '@/api/invoices';
import { getTransactions } from '@/api/transactions';
import {
  AmountCurrency,
  AmountsCurrency,
  AppCard,
  DataTable,
  RelativeDate,
  TagList,
  type DataTableColumn,
} from '@/components/ui';
import { useAuthStore } from '@/stores/auth';
import type { Entity, Invoice, Transaction } from '@/types/api';

const LIMIT = 20;

export const Profile = () => {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const actorEntity = useAuthStore((state) => state.actorEntity);

  const tab = searchParams.get('tab') ?? 'profile';

  const parsedId = id ? parseInt(id, 10) : undefined;
  const profileId =
    id === undefined
      ? actorEntity?.id
      : Number.isNaN(parsedId!)
        ? undefined
        : parsedId;
  const isOwnProfile = profileId != null && profileId === actorEntity?.id;

  useEffect(() => {
    if (!id && actorEntity) {
      navigate(`/profile/${actorEntity.id}`, { replace: true });
    }
  }, [id, actorEntity, navigate]);

  const { data: entity, isError: entityError, isLoading: entityLoading } = useQuery({
    queryKey: ['entities', profileId],
    queryFn: () => (isOwnProfile ? getMe() : getEntity(profileId!)),
    enabled: !!profileId,
  });

  const { data: balances } = useQuery({
    queryKey: ['balances', profileId],
    queryFn: () => (profileId ? getBalances(profileId) : null),
    enabled: !!profileId,
  });

  const { data: transactionsData } = useQuery({
    queryKey: ['transactions', profileId],
    queryFn: () =>
      profileId ? getTransactions({ entity_id: profileId, limit: LIMIT }) : null,
    enabled: !!profileId,
  });

  const { data: invoicesData } = useQuery({
    queryKey: ['invoices', profileId],
    queryFn: () => (profileId ? getInvoices({ entity_id: profileId, limit: LIMIT }) : null),
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
  const copyToClipboard = useCallback((text: string) => {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, []);

  if (!actorEntity) {
    return (
      <Stack gap="md">
        <Text c="dimmed">Loading profile...</Text>
      </Stack>
    );
  }

  if (profileId == null) {
    return (
      <Stack gap="md">
        <Text c="dimmed">{id ? 'Profile not found.' : 'Loading profile...'}</Text>
      </Stack>
    );
  }

  if (entityError || (profileId && !entity && !entityLoading)) {
    return (
      <Stack gap="md">
        <Text c="dimmed">Profile not found.</Text>
      </Stack>
    );
  }

  if (entityLoading || !entity) {
    return (
      <Stack gap="md">
        <Text c="dimmed">Loading profile...</Text>
      </Stack>
    );
  }

  const profileEntity = entity as Entity;

  const EntityLink = ({ entityRef }: { entityRef: { id: number; name: string } }) => (
    <Anchor size="sm" component={Link} to={`/profile/${entityRef.id}`} underline="hover" inherit>
      {entityRef.name}
    </Anchor>
  );

  const transactionColumns: DataTableColumn<Transaction>[] = [
    { key: 'id', label: 'ID', render: (r) => <Text size="sm">{r.id}</Text> },
    {
      key: 'created_at',
      label: 'Date',
      render: (r) => <RelativeDate isoString={r.created_at} />,
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
      key: 'amount',
      label: 'Amount',
      render: (r) => <AmountCurrency amount={r.amount} currency={r.currency} />,
    },
    {
      key: 'treasury',
      label: 'Treasury',
      render: (r) => {
        const hasTreasury = r.from_treasury_id ?? r.to_treasury_id;
        if (!hasTreasury) return <Text size="sm">—</Text>;
        return (
          <Text size="sm">
            {r.from_treasury?.name ?? 'x'} → {r.to_treasury?.name ?? 'x'}
          </Text>
        );
      },
    },
    {
      key: 'tags',
      label: 'Tags',
      render: (r) => (r.tags.length ? <TagList tags={r.tags} /> : <Text size="sm">—</Text>),
    },
    { key: 'comment', label: 'Comment', render: (r) => <Text size="sm">{r.comment || '—'}</Text> },
    {
      key: 'invoice_id',
      label: 'Invoice',
      render: (r) => (r.invoice_id ? <Text size="sm">{r.invoice_id}</Text> : <Text size="sm">—</Text>),
    },
    {
      key: 'status',
      label: 'Status',
      render: (r) => (
        <Text size="sm" c={r.status === 'completed' ? 'green' : 'gray'}>
          {r.status}
        </Text>
      ),
    },
    {
      key: 'actor_entity',
      label: 'Actor',
      render: (r) => <EntityLink entityRef={r.actor_entity} />,
    },
  ];

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
        <Text
          size="sm"
          c={
            r.status === 'paid'
              ? 'green'
              : r.status === 'cancelled'
                ? 'red'
                : 'gray'
          }
        >
          {r.status}
        </Text>
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
      <Tabs
        value={tab}
        onChange={(v) => setSearchParams({ tab: v ?? 'profile' })}
      >
        <Tabs.List>
          <Tabs.Tab value="profile">Profile</Tabs.Tab>
          <Tabs.Tab value="statistics">Statistics</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="profile">
          <Stack gap="lg" mt="md">
      <AppCard>
        <Stack gap="md">
          <Flex gap="sm" align="center" wrap="nowrap">
            <Text size="xl" fw={700} lh={1}>
              {e.name}
            </Text>
            {isOwnProfile && (
              <Badge
                size="sm"
                variant="light"
                color="blue"
                className="shrink-0 leading-none mt-px"
              >
                This is you
              </Badge>
            )}
          </Flex>
          <Group gap="md">
            <Text size="sm" c="dimmed">
              ID: {e.id}
            </Text>
            <Text size="sm" c="dimmed">
              Name: {e.name}
            </Text>
            <Badge size="sm" color={e.active ? 'green' : 'gray'}>
              {e.active ? 'Active' : 'Inactive'}
            </Badge>
          </Group>
          {e?.tags?.length ? <TagList tags={e.tags} showAll /> : null}
          {e?.created_at && (
            <Text size="sm" c="dimmed" component="span">
              Created: <RelativeDate isoString={e.created_at} />
            </Text>
          )}

          {isOwnProfile && (e?.auth?.telegram_id || e?.auth?.signal_id) && (
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
          )}
        </Stack>
      </AppCard>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Balance
        </Text>
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
          <Text size="sm" c="dimmed">
            No transactions.
          </Text>
        )}
      </AppCard>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Latest Transactions
        </Text>
        <DataTable
          columns={transactionColumns}
          data={transactions}
          emptyMessage="No transactions."
        />
      </AppCard>

      <AppCard>
        <Text size="lg" fw={600} mb="md">
          Invoices
        </Text>
        <DataTable columns={invoiceColumns} data={invoices} emptyMessage="No invoices." />
      </AppCard>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="statistics">
          <Text size="xl" fw={900} mt="md">
            Statistics
          </Text>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};
