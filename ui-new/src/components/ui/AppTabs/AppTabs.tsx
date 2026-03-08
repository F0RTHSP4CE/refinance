import { Tabs, type TabsProps } from '@mantine/core';
import { APP_TABS_CLASSNAMES, mergeClassNames } from '../sharedInputStyles';

const APP_TABS_STYLES: NonNullable<TabsProps['styles']> = {
  list: {
    gap: '1rem',
    padding: 0,
    borderRadius: 0,
    background: 'transparent',
    border: 0,
    borderBottom: '1px solid var(--app-panel-border)',
    boxShadow: 'none',
  },
  tab: {
    position: 'relative',
    minHeight: 'unset',
    padding: '0.15rem 0 0.9rem',
    marginBottom: '-1px',
    borderRadius: 0,
    color: 'rgba(174, 185, 200, 0.78)',
    fontWeight: 700,
    border: 0,
    background: 'transparent',
    boxShadow: 'none',
    opacity: 0.9,
    transition: 'color 160ms ease, opacity 160ms ease, background 160ms ease',
  },
  tabLabel: {
    fontSize: '0.95rem',
    letterSpacing: '-0.01em',
    color: 'inherit !important',
    fontWeight: 'inherit',
  },
  panel: {
    paddingTop: '1rem',
  },
} as const;

type AppTabsComponent = typeof Tabs;

export const AppTabs = (({ styles, classNames, ...props }: TabsProps) => {
  return (
    <Tabs
      styles={{ ...APP_TABS_STYLES, ...styles }}
      classNames={mergeClassNames(APP_TABS_CLASSNAMES, classNames)}
      {...props}
    />
  );
}) as AppTabsComponent;

AppTabs.List = Tabs.List;
AppTabs.Tab = Tabs.Tab;
AppTabs.Panel = Tabs.Panel;
