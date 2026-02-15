import { Button, Group, Menu, Modal, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { getBalances } from '@/api/balance';
import { useAuthStore } from '@/stores/auth';
import { CardTopUpModal } from '@/pages/TopUp/Card';
import logo from '@/assets/logo.png';

export const Navbar = () => {
  const [opened, { open, close }] = useDisclosure(false);
  const [cardModalOpened, { open: openCardModal, close: closeCardModal }] = useDisclosure(false);
  const clearSession = useAuthStore((state) => state.clearSession);
  const actorEntity = useAuthStore((state) => state.actorEntity);

  const handleLogout = () => {
    clearSession();
    close();
  };

  const { data: balances } = useQuery({
    queryKey: ['balances', actorEntity?.id],
    queryFn: () => (actorEntity ? getBalances(actorEntity.id) : null),
    enabled: !!actorEntity,
    refetchInterval: 30000, // Refresh every 30s
  });

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
      <Link to="/" style={{ display: 'flex' }}>
        <img src={logo} alt="Refinance" className="max-w-[155px]" />
      </Link>

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
                    <div
                      key={currency}
                      style={{
                        position: 'relative',
                        textAlign: 'left',
                      }}
                    >
                      <Text size="sm" fw={500} style={{ lineHeight: 1.2 }}>
                        {completed} {currency.toUpperCase()}
                      </Text>
                      {hasDraft && (
                        <Text
                          size="xs"
                          c="dimmed"
                          style={{
                            position: 'absolute',
                            bottom: '-80%',
                            left: 0,
                            lineHeight: 1,
                          }}
                        >
                          {parseFloat(draft) > 0 ? '+' : ''}
                          {draft}
                        </Text>
                      )}
                    </div>
                  );
                })}
            </Group>

            <Menu shadow="md" width={200}>
              <Menu.Target>
                <Button variant="light">Top Up</Button>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Item onClick={openCardModal}>
                  By card
                </Menu.Item>
                <Menu.Item component={Link} to="/top-up/manual">
                  Cash / Bank / Crypto
                </Menu.Item>
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
