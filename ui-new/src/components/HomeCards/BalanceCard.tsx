import { Button, Card, Group, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';
import { getBalances } from '@/api/balance';
import { CardTopUpModal } from '@/pages/TopUp/Card';
import { RequestMoneyModal, ExchangeModal, IconExchange } from '@/components/PaymentModals';

export const BalanceCard = () => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  const [cardModalOpened, { open: openCardModal, close: closeCardModal }] = useDisclosure(false);
  const [requestMoneyOpened, setRequestMoneyOpened] = useState(false);
  const [exchangeModalOpened, { open: openExchangeModal, close: closeExchangeModal }] = useDisclosure(false);

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
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Group justify="space-between">
            <Text size="lg" fw={700}>
              Balance
            </Text>
            <Button variant="default" size="xs" onClick={openExchangeModal} leftSection={<IconExchange size={16} />}>
              Exchange
            </Button>
          </Group>

          {balanceEntries.length > 0 ? (
            <Group gap="sm">
              {balanceEntries.map(([currency, amount]) => {
                const numAmount = parseFloat(amount);
                const isNegative = numAmount < 0;
                return (
                  <Stack key={currency} gap={2}>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      {currency}
                    </Text>
                    <Text size="xl" fw={900} c={isNegative ? 'red' : undefined}>
                      {numAmount.toFixed(2)}
                    </Text>
                  </Stack>
                );
              })}
            </Group>
          ) : (
            <Text c="dimmed">No balance yet.</Text>
          )}

          <Group gap="xs" grow>
            <Button variant="default" onClick={openCardModal}>
              Top up by card
            </Button>
            <Button variant="default" component={Link} to="/top-up/manual">
              Cash / Bank / Crypto
            </Button>
            <Button variant="default" onClick={() => setRequestMoneyOpened(true)}>
              Request money
            </Button>
          </Group>
        </Stack>
      </Card>

      <CardTopUpModal opened={cardModalOpened} onClose={closeCardModal} />
      <RequestMoneyModal
        opened={requestMoneyOpened}
        onClose={() => setRequestMoneyOpened(false)}
      />
      <ExchangeModal
        opened={exchangeModalOpened}
        onClose={closeExchangeModal}
      />
    </>
  );
};
