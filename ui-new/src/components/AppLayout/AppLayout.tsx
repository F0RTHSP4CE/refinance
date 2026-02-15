import { AppShell } from '@mantine/core';
import { Outlet } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';

export const AppLayout = () => {
  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Navbar />
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
};
