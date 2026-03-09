import { ActionIcon, Button, Group, Menu, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconChevronDown, IconPlus } from '@tabler/icons-react';
import type { ReactNode } from 'react';

export type ActionMenuItem = {
  key: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  color?: string;
  disabled?: boolean;
  onClick: () => void;
};

type ActionMenuProps = {
  label?: string;
  items: ActionMenuItem[];
  compactLabel?: string;
};

export const ActionMenu = ({
  label = 'New payment',
  items,
  compactLabel = 'New',
}: ActionMenuProps) => {
  const isDesktop = useMediaQuery('(min-width: 48em)', true, {
    getInitialValueInEffect: false,
  });

  return (
    <Menu shadow="lg" width={260} position="bottom-end" withinPortal>
      <Menu.Target>
        {isDesktop ? (
          <Button
            variant="default"
            rightSection={<IconChevronDown size={14} />}
            leftSection={<IconPlus size={16} />}
          >
            {label}
          </Button>
        ) : (
          <ActionIcon
            variant="default"
            size={42}
            radius="xl"
            aria-label={compactLabel}
            style={{ boxShadow: 'var(--app-shadow-soft)' }}
          >
            <IconPlus size={20} />
          </ActionIcon>
        )}
      </Menu.Target>

      <Menu.Dropdown
        style={{
          background: 'var(--app-surface-2)',
          border: '1px solid var(--app-border-subtle)',
        }}
      >
        {items.map((item) => (
          <Menu.Item
            key={item.key}
            disabled={item.disabled}
            color={item.color}
            leftSection={item.icon}
            onClick={item.onClick}
          >
            <Group gap={0} align="start">
              <Stack gap={2}>
                <Text fw={700} size="sm">
                  {item.label}
                </Text>
                {item.description ? (
                  <Text size="xs" className="app-muted-copy">
                    {item.description}
                  </Text>
                ) : null}
              </Stack>
            </Group>
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
};
