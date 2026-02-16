import { Anchor, Burger, Button, Group, Menu, Modal, Stack, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';
import { CardTopUpModal } from '@/pages/TopUp/Card';
import { RequestMoneyModal, ExchangeModal } from '@/components/PaymentModals';
import { POLLING_INTERVALS } from '@/constants/polling';
import logo from '@/assets/logo.png';

const NAV_LINKS = [
  { to: '/', label: 'Home' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/invoices', label: 'Invoices' },
  { to: '/deposits', label: 'Deposits' },
  { to: '/fee', label: 'Fee' },
  { to: '/splits', label: 'Split' },
  { to: '/stats', label: 'Stats' },
  { to: '/users', label: 'Users' },
] as const;

export const Navbar = () => {
  const [opened, { open, close }] = useDisclosure(false);
  const [cardModalOpened, { open: openCardModal, close: closeCardModal }] = useDisclosure(false);
  const [burgerOpened, { open: openBurger, close: closeBurger }] = useDisclosure(false);
  const [requestMoneyOpened, setRequestMoneyOpened] = useState(false);
  const [exchangeModalOpened, { open: openExchangeModal, close: closeExchangeModal }] = useDisclosure(false);
  const clearSession = useAuthStore((state) => state.clearSession);
  const actorEntity = useAuthStore((state) => state.actorEntity);

  const handleLogout = () => {
    clearSession();
    close();
  };

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: ({ signal }) => (actorEntity ? getBalances(actorEntity.id, signal) : null),
    enabled: !!actorEntity,
    refetchInterval: POLLING_INTERVALS.BALANCES,
  });

  const { pathname } = useLocation();

  const currencies = useMemo(() => {
    if (!balances) return [];
    const allCurrencies = new Set([
      ...Object.keys(balances.completed || {}),
      ...Object.keys(balances.draft || {}),
    ]);
    return Array.from(allCurrencies);
  }, [balances]);

  return (
    <Group h="100%" px="md" justify="space-between">
      <Group gap="xl">
        <Link to="/" className="flex shrink-0">
          <img src={logo} alt="Refinance" className="max-w-[155px]" />
        </Link>
        <Group gap="xl" className="overflow-x-auto">
          {NAV_LINKS.map(({ to, label }) => {
            const isActive = pathname === to;
            return (
              <Anchor
                key={to}
                component={Link}
                to={to}
                underline="never"
                inherit={!isActive}
                c={isActive ? 'green.5' : undefined}
                className="shrink-0 whitespace-nowrap text-xl no-underline hover:text-white hover:no-underline transition-colors"
              >
                {label}
              </Anchor>
            );
          })}
        </Group>
        <Menu
          shadow="md"
          width={200}
          opened={burgerOpened}
          onChange={(v) => (v ? openBurger() : closeBurger())}
          closeOnItemClick
        >
          <Menu.Target>
            <Burger opened={burgerOpened} />
          </Menu.Target>

          <Menu.Dropdown>
            <Menu.Item component={Link} to="/treasuries">
              Treasuries
            </Menu.Item>
            <Menu.Item component={Link} to="/tags">
              Tags
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>

      <Group>
        {actorEntity && (
          <>
            <Group gap="md">
              {balances &&
                currencies.map((currency) => {
                  const completed = balances.completed?.[currency] ?? '0';
                  const draft = balances.draft?.[currency];
                  const hasDraft = draft && parseFloat(draft) !== 0;

                  return (
                    <Stack key={currency} gap={0} className="text-left">
                      <Text size="sm" fw={500} lh={1.2}>
                        {completed} {currency.toUpperCase()}
                      </Text>
                      {hasDraft && (
                        <Text size="xs" c="dimmed" lh={1}>
                          {parseFloat(draft) > 0 ? '+' : ''}
                          {draft}
                        </Text>
                      )}
                    </Stack>
                  );
                })}
            </Group>

            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Button variant="light">Top Up</Button>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Item onClick={openCardModal}>By card</Menu.Item>
                <Menu.Item component={Link} to="/top-up/manual">
                  Cash / Bank / Crypto
                </Menu.Item>
                <Menu.Item onClick={() => setRequestMoneyOpened(true)}>Request Money</Menu.Item>
                <Menu.Divider />
                <Menu.Item onClick={openExchangeModal}>Exchange</Menu.Item>
              </Menu.Dropdown>
            </Menu>

            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Button variant="light">{actorEntity.name}</Button>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Item component={Link} to={`/profile/${actorEntity.id}`}>
                  Profile
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item color="red" onClick={open}>
                  Logout
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </>
        )}

        {!actorEntity && (
          <Button variant="subtle" color="red" onClick={open}>
            Logout
          </Button>
        )}
      </Group>

      <CardTopUpModal opened={cardModalOpened} onClose={closeCardModal} />
      <RequestMoneyModal
        opened={requestMoneyOpened}
        onClose={() => setRequestMoneyOpened(false)}
      />
      <ExchangeModal
        opened={exchangeModalOpened}
        onClose={closeExchangeModal}
      />

      <Modal opened={opened} onClose={close} title="Logout" centered>
        <Text size="sm" c="dimmed" mb="md">
          Are you sure you want to logout?
        </Text>
        <Group justify="flex-end" gap="xs">
          <Button variant="subtle" onClick={close}>
            Cancel
          </Button>
          <Button color="red" onClick={handleLogout}>
            Logout
          </Button>
        </Group>
      </Modal>
    </Group>
  );
};
