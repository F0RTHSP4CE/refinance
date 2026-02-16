import { Card, Group, Stack, Text, Badge, Button, Anchor } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';
import { getPendingInvoices } from '@/api/invoices';

export const InvoicesCard = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);

  const { data: invoicesResponse } = useQuery({
    queryKey: ['pendingInvoices', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity
        ? getPendingInvoices({ from_entity_id: actorEntity.id, limit: 10, signal })
        : Promise.resolve({ items: [], total: 0, skip: 0, limit: 10 }),
    enabled: actorEntity !== null,
  });

  const invoices = invoicesResponse?.items ?? [];
  const totalCount = invoicesResponse?.total ?? 0;
  const nextInvoice = invoices[0];
  const otherInvoices = invoices.slice(1);

  const formatBillingPeriod = (period: string | null | undefined) => {
    if (!period) return null;
    const date = new Date(period);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  const formatAmounts = (amounts: { currency: string; amount: string }[]) => {
    return amounts
      .map((a) => `${parseFloat(a.amount).toFixed(2)} ${a.currency.toUpperCase()}`)
      .join(' + ');
  };

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Text size="lg" fw={700}>
            Fee / Invoices
          </Text>
          {totalCount > 0 && (
            <Badge color="red" size="lg">
              {totalCount}
            </Badge>
          )}
        </Group>

        {totalCount === 0 ? (
          <>
            <Text c="dimmed">No unpaid invoices</Text>
            <Text size="sm" c="dimmed">
              Top up your balance so invoices are paid automatically.
            </Text>
          </>
        ) : (
          <>
            {nextInvoice && (
              <Stack gap="xs">
                <Text size="xs" c="dimmed" fw={600}>
                  NEXT DUE:
                </Text>
                <Card
                  component={Link}
                  to={`/invoices/${nextInvoice.id}`}
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
                    <Button size="xs" variant="light" color="red">
                      Pay
                    </Button>
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
                    <Anchor size="sm" component={Link} to={`/invoices/${invoice.id}`}>
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

            <Text size="sm" c="dimmed">
              Top up your balance! Invoices will be paid automatically.
            </Text>
          </>
        )}
      </Stack>
    </Card>
  );
};
