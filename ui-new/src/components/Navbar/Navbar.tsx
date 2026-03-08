import {
  Anchor,
  Box,
  Burger,
  Button,
  Divider,
  Drawer,
  Group,
  Menu,
  Stack,
  Text,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import {
  IconArrowsExchange,
  IconArrowsSplit2,
  IconChevronDown,
  IconCreditCard,
  IconHome2,
  IconLogout,
  IconReceipt2,
  IconRepeat,
  IconSettings,
  IconUserCircle,
  IconUsersGroup,
} from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getBalances } from '@/api/balance';
import { ActionMenu, AppModal, AppModalFooter, ModalStepHeader } from '@/components/ui';
import { APP_BRAND, NAV_LABELS } from '@/content/uiVocabulary';
import { useAuthStore } from '@/stores/auth';
import { CardTopUpModal } from '@/pages/TopUp/Card';
import { ExchangeModal } from '@/components/PaymentModals';
import { MoneyActionModal } from '@/components/MoneyActionModal/MoneyActionModal';
import { POLLING_INTERVALS } from '@/constants/polling';
import logo from '@/assets/logo.png';
import { getActiveLinkTextProps, isLinkActive } from './utils';

type NavLinkItem = {
  to: string;
  label: string;
  icon?: typeof IconHome2;
};

const PRIMARY_LINKS: readonly NavLinkItem[] = [
  { to: '/', label: NAV_LABELS.home, icon: IconHome2 },
  { to: '/transactions', label: NAV_LABELS.transactions, icon: IconRepeat },
  { to: '/fee', label: NAV_LABELS.fee, icon: IconReceipt2 },
  { to: '/splits', label: NAV_LABELS.splits, icon: IconArrowsSplit2 },
  { to: '/stats', label: NAV_LABELS.stats, icon: IconUsersGroup },
] as const;

const SECONDARY_LINKS: readonly NavLinkItem[] = [
  { to: '/users', label: NAV_LABELS.users },
  { to: '/entities', label: NAV_LABELS.entities },
  { to: '/treasuries', label: NAV_LABELS.treasuries },
  { to: '/tags', label: NAV_LABELS.tags },
] as const;

export const Navbar = () => {
  const [logoutOpened, { open: openLogout, close: closeLogout }] = useDisclosure(false);
  const [cardModalOpened, { open: openCardModal, close: closeCardModal }] = useDisclosure(false);
  const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
  const [requestMoneyOpened, setRequestMoneyOpened] = useState(false);
  const [transferOpened, setTransferOpened] = useState(false);
  const [desktopMenuOpened, setDesktopMenuOpened] = useState(false);
  const [exchangeModalOpened, { open: openExchangeModal, close: closeExchangeModal }] =
    useDisclosure(false);
  const clearSession = useAuthStore((state) => state.clearSession);
  const actorEntity = useAuthStore((state) => state.actorEntity);

  const handleLogout = () => {
    clearSession();
    closeLogout();
    closeDrawer();
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

  const actionItems = [
    {
      key: 'top-up',
      label: 'Top up by card',
      description: 'Add funds to your personal balance',
      icon: <IconCreditCard size={16} />,
      onClick: openCardModal,
    },
    {
      key: 'request',
      label: 'Request money',
      description: 'Create a pending dues or payback request',
      icon: <IconReceipt2 size={16} />,
      onClick: () => setRequestMoneyOpened(true),
    },
    {
      key: 'transfer',
      label: 'Create transfer',
      description: 'Move funds between members, entities, or funds',
      icon: <IconRepeat size={16} />,
      onClick: () => setTransferOpened(true),
    },
    {
      key: 'exchange',
      label: 'Exchange balance',
      description: 'Rebalance currencies inside your stash',
      icon: <IconArrowsExchange size={16} />,
      onClick: openExchangeModal,
    },
  ];

  const renderDesktopLink = (to: string, label: string) => {
    const isActive = isLinkActive(pathname, to);
    const { c, fw } = getActiveLinkTextProps(isActive);

    return (
      <Anchor
        key={to}
        component={Link}
        to={to}
        underline="never"
        c={c}
        fw={fw}
        className="shrink-0 whitespace-nowrap no-underline hover:no-underline"
        style={{
          borderBottom: isActive ? '2px solid var(--app-accent)' : '2px solid transparent',
          paddingBottom: '0.35rem',
          transition: 'color 160ms ease, border-color 160ms ease',
        }}
      >
        {label}
      </Anchor>
    );
  };

  const secondaryActive = SECONDARY_LINKS.some(({ to }) => isLinkActive(pathname, to));

  return (
    <>
      <Group h="100%" px={{ base: 'sm', sm: 'lg' }} justify="space-between" wrap="nowrap">
        <Group gap="lg" wrap="nowrap">
          <Box hiddenFrom="sm">
            <Burger
              opened={drawerOpened}
              onClick={drawerOpened ? closeDrawer : openDrawer}
              aria-label="Open navigation"
            />
          </Box>

          <Link to="/" className="flex shrink-0">
            <img src={logo} alt={APP_BRAND.logoAlt} className="max-w-[128px] sm:max-w-[148px]" />
          </Link>

          <Group gap="lg" visibleFrom="sm" wrap="nowrap">
            {PRIMARY_LINKS.map(({ to, label }) => renderDesktopLink(to, label))}
          </Group>

          <Box visibleFrom="sm">
            <Menu
              shadow="lg"
              width={220}
              withinPortal
              opened={desktopMenuOpened}
              onChange={setDesktopMenuOpened}
            >
              <Menu.Target>
                <Burger
                  opened={desktopMenuOpened}
                  onClick={() => setDesktopMenuOpened((current) => !current)}
                  size="sm"
                  color={secondaryActive ? 'var(--app-accent)' : 'var(--app-text-primary)'}
                  aria-label="Open secondary navigation"
                />
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Secondary navigation</Menu.Label>
                {SECONDARY_LINKS.map(({ to, label }) => {
                  const active = isLinkActive(pathname, to);
                  return (
                    <Menu.Item
                      key={to}
                      component={Link}
                      to={to}
                      style={{
                        color: active ? 'var(--app-accent)' : undefined,
                        background: active ? 'rgba(155, 227, 65, 0.12)' : undefined,
                        border: active ? '1px solid rgba(155, 227, 65, 0.18)' : undefined,
                      }}
                    >
                      {label}
                    </Menu.Item>
                  );
                })}
              </Menu.Dropdown>
            </Menu>
          </Box>
        </Group>

        <Group gap="sm" wrap="nowrap">
          {actorEntity ? <ActionMenu items={actionItems} /> : null}

          {actorEntity ? (
            <Box visibleFrom="sm">
              <Menu shadow="lg" width={240} withinPortal>
                <Menu.Target>
                  <Button variant="subtle" rightSection={<IconChevronDown size={14} />}>
                    {actorEntity.name}
                  </Button>
                </Menu.Target>
                <Menu.Dropdown
                  style={{
                    background: 'var(--app-surface-2)',
                    border: '1px solid var(--app-border-subtle)',
                  }}
                >
                  <Menu.Label>{APP_BRAND.shortName}</Menu.Label>
                  <Menu.Item
                    component={Link}
                    to={`/profile/${actorEntity.id}`}
                    leftSection={<IconUserCircle size={16} />}
                  >
                    My profile
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Item
                    color="red"
                    leftSection={<IconLogout size={16} />}
                    onClick={openLogout}
                  >
                    Sign out
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Box>
          ) : null}
        </Group>
      </Group>

      <Drawer
        opened={drawerOpened}
        onClose={closeDrawer}
        padding="md"
        size="100%"
        title={APP_BRAND.shortName}
      >
        <Stack gap="xl">
          {actorEntity ? (
            <Stack gap="md">
              <Stack gap={4}>
                <Text className="app-kicker">{APP_BRAND.name}</Text>
                <Text fw={800} size="xl">
                  {actorEntity.name}
                </Text>
              </Stack>

              {balances ? (
                <Group gap="xs" wrap="wrap">
                  {currencies.map((currency) => {
                    const completed = balances.completed?.[currency] ?? '0';
                    const draft = balances.draft?.[currency];
                    const hasDraft = draft && parseFloat(draft) !== 0;

                    return (
                      <Box key={currency} className="app-header-chip">
                        <Text fw={700} size="sm">
                          {completed} {currency.toUpperCase()}
                        </Text>
                        {hasDraft ? (
                          <Text size="xs" className="app-muted-copy">
                            {parseFloat(draft) > 0 ? '+' : ''}
                            {draft} draft
                          </Text>
                        ) : null}
                      </Box>
                    );
                  })}
                </Group>
              ) : null}
            </Stack>
          ) : null}

          <Stack gap="xs">
            <Text className="app-kicker">Navigate the stack</Text>
            {[...PRIMARY_LINKS, ...SECONDARY_LINKS].map(({ to, label, icon: Icon }) => {
              const isActive = isLinkActive(pathname, to);
              return (
                <Button
                  key={to}
                  component={Link}
                  to={to}
                  justify="start"
                  variant={isActive ? 'filled' : 'subtle'}
                  leftSection={Icon ? <Icon size={16} /> : <IconSettings size={16} />}
                  onClick={closeDrawer}
                >
                  {label}
                </Button>
              );
            })}
          </Stack>

          {actorEntity ? (
            <>
              <Divider />
              <Stack gap="xs">
                <Text className="app-kicker">Account</Text>
                <Button
                  component={Link}
                  to={`/profile/${actorEntity.id}`}
                  justify="start"
                  variant="subtle"
                  leftSection={<IconUserCircle size={16} />}
                  onClick={closeDrawer}
                >
                  My profile
                </Button>
                <Button
                  justify="start"
                  variant="subtle"
                  color="red"
                  leftSection={<IconLogout size={16} />}
                  onClick={openLogout}
                >
                  Sign out
                </Button>
              </Stack>
            </>
          ) : null}
        </Stack>
      </Drawer>

      <CardTopUpModal opened={cardModalOpened} onClose={closeCardModal} />
      <MoneyActionModal
        opened={requestMoneyOpened}
        mode="request"
        onClose={() => setRequestMoneyOpened(false)}
        initialToEntityId={actorEntity?.id}
      />
      <MoneyActionModal
        opened={transferOpened}
        mode="transfer"
        onClose={() => setTransferOpened(false)}
        initialFromEntityId={actorEntity?.id}
      />
      <ExchangeModal opened={exchangeModalOpened} onClose={closeExchangeModal} />

      <AppModal
        opened={logoutOpened}
        onClose={closeLogout}
        variant="compact"
        title="Sign out"
        subtitle={`End this ${APP_BRAND.shortName} session and return to sign-in.`}
        footer={
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={closeLogout}>
                Cancel
              </Button>
            }
            primary={
              <Button color="red" onClick={handleLogout}>
                Sign out
              </Button>
            }
          />
        }
      >
        <ModalStepHeader
          eyebrow="Account"
          title="Are you sure?"
          description="You will need to authenticate again before you can resume finance operations."
        />
      </AppModal>
    </>
  );
};
