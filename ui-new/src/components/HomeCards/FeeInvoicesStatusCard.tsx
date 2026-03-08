import { Anchor, Card, Group, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getPendingInvoices } from '@/api/invoices';
import { useAuthStore } from '@/stores/auth';
import { StatusBadge } from '@/components/ui';

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
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Text size="lg" fw={700}>
            Fee / Invoices
          </Text>
          {pendingCount > 0 && (
            <StatusBadge size="lg" tone="neutral">
              {pendingCount}
            </StatusBadge>
          )}
        </Group>

        {pendingCount === 0 ? (
          <Text c="dimmed">No unpaid invoices</Text>
        ) : (
          <>
            {nextInvoice && (
              <Stack gap="xs">
                <Text size="xs" c="dimmed" fw={600}>
                  NEXT DUE:
                </Text>
                <Card
                  component={Link}
                  to={`/fee?tab=invoices&invoiceId=${nextInvoice.id}`}
                  padding="sm"
                  radius="md"
                  withBorder
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  <Group justify="space-between" align="center">
                    <Stack gap={2}>
                      <Text size="lg" fw={700} c="red">
                        {formatAmounts(nextInvoice.amounts)}
                      </Text>
                      {nextInvoice.billing_period && (
                        <Text size="sm" c="dimmed">
                          {formatBillingPeriod(nextInvoice.billing_period)}
                        </Text>
                      )}
                    </Stack>
                    <StatusBadge tone="neutral">pending</StatusBadge>
                  </Group>
                </Card>
              </Stack>
            )}

            {otherInvoices.length > 0 && (
              <Stack gap="xs">
                <Text size="xs" c="dimmed" fw={600}>
                  OTHER PENDING:
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
        <Text size="sm" c="dimmed">
          Top up your balance! Invoices are paid automatically when enough funds are available.
        </Text>
      </Stack>
    </Card>
  );
};
