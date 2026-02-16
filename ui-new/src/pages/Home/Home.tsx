import { SimpleGrid } from '@mantine/core';
import { BalanceCard, InvoicesCard, FridgeCoffeeCard } from '@/components/HomeCards';

export const Home = () => {
  return (
    <SimpleGrid cols={{ base: 1, sm: 3, lg: 3 }} spacing="md">
      <BalanceCard />
      <InvoicesCard />
      <FridgeCoffeeCard />
    </SimpleGrid>
  );
};
