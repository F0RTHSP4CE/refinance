import { Anchor, Button, Group, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getPendingInvoices } from '@/api/invoices';
import { useAuthStore } from '@/stores/auth';
import { EmptyState, SectionCard, StatusBadge } from '@/components/ui';

const LIMIT = 10;

const formatAmount = (amount: string, currency: string) =>
  `${parseFloat(amount).toFixed(2)} ${currency.toUpperCase()}`;

const formatBillingPeriod = (period: string | null | undefined) => {
  if (!period) return null;
  const date = new Date(period);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatAmounts = (amounts: { currency: string; amount: string }[]) =>
  amounts.map((a) => formatAmount(a.amount, a.currency)).join(' + ');

export const FeeInvoicesStatusCard = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);

  const { data: invoicesResponse } = useQuery({
    queryKey: ['pendingInvoices', actorEntity?.id, LIMIT],
    queryFn: ({ signal }) =>
      getPendingInvoices({
        from_entity_id: actorEntity!.id,
        limit: LIMIT,
        signal,
      }),
    enabled: actorEntity !== null,
  });

  const invoices = invoicesResponse?.items ?? [];
  const pendingCount = invoicesResponse?.total ?? 0;
  const nextInvoice = invoices[0];
  const otherInvoices = invoices.slice(1);

  return (
    <SectionCard
      title="Dues to settle"
      description="Keep an eye on the next unpaid invoice so auto-settlement does not bounce."
      action={
        pendingCount > 0 ? (
          <StatusBadge size="lg" tone="warning">
            {pendingCount}
          </StatusBadge>
        ) : null
      }
    >
      <Stack gap="md">
        {pendingCount === 0 ? (
            <EmptyState
              compact
              title="No unpaid dues"
              description="You are clear for now. New dues invoices will show up here as soon as they are issued."
            />
        ) : (
          <>
            {nextInvoice && (
              <Stack gap="xs">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Next to settle
                </Text>
                <Anchor
                  component={Link}
                  to={`/fee?tab=invoices&invoiceId=${nextInvoice.id}`}
                  underline="never"
                  style={{
                    display: 'block',
                    textDecoration: 'none',
                    color: 'inherit',
                    padding: '0.95rem',
                    borderRadius: '0.95rem',
                    border: '1px solid rgba(255, 122, 120, 0.18)',
                    background: 'rgba(255, 122, 120, 0.06)',
                  }}
                >
                  <Group justify="space-between" align="center">
                    <Stack gap={2}>
                      <Text size="lg" fw={800} c="var(--app-danger)">
                        {formatAmounts(nextInvoice.amounts)}
                      </Text>
                      {nextInvoice.billing_period && (
                        <Text size="sm" c="dimmed">
                          {formatBillingPeriod(nextInvoice.billing_period)}
                        </Text>
                      )}
                    </Stack>
                    <StatusBadge tone="warning">pending</StatusBadge>
                  </Group>
                </Anchor>
              </Stack>
            )}

            {otherInvoices.length > 0 && (
              <Stack gap="xs">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Other open invoices
                </Text>
                {otherInvoices.map((invoice) => (
                  <Group key={invoice.id} justify="space-between" align="center">
                    <Anchor
                      size="sm"
                      component={Link}
                      to={`/fee?tab=invoices&invoiceId=${invoice.id}`}
                    >
                      {formatAmounts(invoice.amounts)}
                      {invoice.billing_period && (
                        <Text span c="dimmed" ml={4}>
                          - {formatBillingPeriod(invoice.billing_period)}
                        </Text>
                      )}
                    </Anchor>
                  </Group>
                ))}
              </Stack>
            )}
          </>
        )}
        <Group justify="space-between" align="center" wrap="wrap">
          <Text size="sm" className="app-muted-copy">
            Dues invoices settle automatically as soon as your balance is high enough.
          </Text>
          <Button component={Link} to="/fee?tab=invoices" variant="subtle" size="sm">
            Open dues
          </Button>
        </Group>
      </Stack>
    </SectionCard>
  );
};
