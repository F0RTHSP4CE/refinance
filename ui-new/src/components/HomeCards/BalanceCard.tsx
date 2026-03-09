import { Button, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useDisclosure } from '@mantine/hooks';
import { useAuthStore } from '@/stores/auth';
import { getBalances } from '@/api/balance';
import { CardTopUpModal } from '@/pages/TopUp/Card';
import { ExchangeModal, IconExchange } from '@/components/PaymentModals';
import { AccentSurface, EmptyState, StatusBadge } from '@/components/ui';

export const BalanceCard = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const [cardModalOpened, { open: openCardModal, close: closeCardModal }] = useDisclosure(false);
  const [exchangeModalOpened, { open: openExchangeModal, close: closeExchangeModal }] =
    useDisclosure(false);

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) =>
      actorEntity ? getBalances(actorEntity.id, signal) : Promise.resolve(null),
    enabled: actorEntity !== null,
  });

  const completedBalances = balances?.completed ?? {};
  const balanceEntries = Object.entries(completedBalances);

  return (
    <>
      <AccentSurface p="xl">
        <Stack gap="md">
          <Group justify="space-between" align="start" gap="md" wrap="wrap">
            <Stack gap={6}>
              <Text className="app-kicker">Primary stash</Text>
              <Text className="app-section-title">Available balance</Text>
              <Text size="sm" className="app-muted-copy" maw={420}>
                Your fastest read on what you can spend right now. Top up and rebalance here;
                requests and transfers stay in the global action menu.
              </Text>
            </Stack>
            <Group gap="xs">
              <Button variant="default" onClick={openCardModal}>
                Top up by card
              </Button>
              <Button
                variant="outline"
                onClick={openExchangeModal}
                leftSection={<IconExchange size={16} />}
              >
                Exchange
              </Button>
            </Group>
          </Group>

          {balanceEntries.length > 0 ? (
            <SimpleGrid cols={{ base: 1, sm: 2, lg: balanceEntries.length > 2 ? 3 : 2 }} spacing="sm">
              {balanceEntries.map(([currency, amount]) => {
                const numAmount = parseFloat(amount);
                const isNegative = numAmount < 0;
                const draft = balances?.draft?.[currency];
                const hasDraft = draft && parseFloat(draft) !== 0;
                return (
                  <Stack
                    key={currency}
                    gap="xs"
                    p="md"
                    style={{
                      background: 'rgba(255, 255, 255, 0.035)',
                      border: '1px solid var(--app-border-subtle)',
                      borderRadius: '0.95rem',
                    }}
                  >
                    <Group justify="space-between" align="center">
                      <Text size="xs" tt="uppercase" className="app-muted-copy">
                        {currency}
                      </Text>
                      {hasDraft ? <StatusBadge tone="draft">Draft {draft}</StatusBadge> : null}
                    </Group>
                    <Text size="2rem" fw={900} c={isNegative ? 'var(--app-danger)' : undefined}>
                      {numAmount.toFixed(2)}
                    </Text>
                    <Text size="sm" className="app-muted-copy">
                      {isNegative ? 'Needs attention' : 'Available now'}
                    </Text>
                  </Stack>
                );
              })}
            </SimpleGrid>
          ) : (
            <EmptyState
              compact
              title="No balance yet"
              description="Top up once to create your first balance, then use the global action menu for the rest of your finance flows."
            />
          )}

          <Text size="sm" className="app-muted-copy">
            Draft holds stay beside each currency so reserved money never gets confused with spendable cash.
          </Text>
        </Stack>
      </AccentSurface>

      <CardTopUpModal opened={cardModalOpened} onClose={closeCardModal} />
      <ExchangeModal opened={exchangeModalOpened} onClose={closeExchangeModal} />
    </>
  );
};
