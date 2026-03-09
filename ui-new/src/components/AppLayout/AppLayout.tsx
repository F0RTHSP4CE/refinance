import { AppShell } from '@mantine/core';
import { Outlet } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';

export const AppLayout = () => {
  return (
    <AppShell
      header={{ height: { base: 72, sm: 78 } }}
      padding={{ base: 'sm', sm: 'lg' }}
      style={{
        background: 'transparent',
      }}
    >
      <AppShell.Header
        style={{
          background: 'rgba(11, 13, 16, 0.78)',
          borderBottom: '1px solid var(--app-border-subtle)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <Navbar />
      </AppShell.Header>
      <AppShell.Main className="app-shell-main">
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
};
