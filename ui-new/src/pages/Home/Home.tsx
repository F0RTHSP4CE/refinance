import { Box, SimpleGrid, Stack } from '@mantine/core';
import {
  BalanceCard,
  DraftsCard,
  FeeInvoicesStatusCard,
  FridgeCoffeeCard,
  HomeTransactionsTableSection,
} from '@/components/HomeCards';

export const Home = () => {
  return (
    <Stack
      gap="md"
      style={{
        minHeight: 'calc(100dvh - var(--app-shell-header-height, 60px) - 2rem)',
      }}
    >
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 2 }} spacing="md">
        <BalanceCard />
        <FeeInvoicesStatusCard />
        <FridgeCoffeeCard />
        <DraftsCard />
      </SimpleGrid>
      <Box mt="auto">
        <HomeTransactionsTableSection />
      </Box>
    </Stack>
  );
};
