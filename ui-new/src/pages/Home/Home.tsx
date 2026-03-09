import { SimpleGrid, Stack } from '@mantine/core';
import {
  BalanceCard,
  DraftsCard,
  FeeInvoicesStatusCard,
  FridgeCoffeeCard,
  HomeTransactionsTableSection,
} from '@/components/HomeCards';
import { PageHeader } from '@/components/ui';
import { APP_BRAND } from '@/content/uiVocabulary';

export const Home = () => {
  return (
    <Stack
      gap="lg"
      style={{
        minHeight: 'calc(100dvh - var(--app-shell-header-height, 60px) - 2rem)',
      }}
    >
      <PageHeader
        eyebrow={APP_BRAND.name}
        title="Keep the space funded"
        subtitle="Start with what needs action now: your available balance, dues to settle, draft activity, and the latest movement across F0RTHSP4CE."
        variant="hero"
      />

      <BalanceCard />

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md" data-testid="home-secondary-grid">
        <div className="h-full">
          <FeeInvoicesStatusCard />
        </div>
        <div className="h-full">
          <DraftsCard />
        </div>
        <div className="h-full">
          <FridgeCoffeeCard />
        </div>
      </SimpleGrid>

      <HomeTransactionsTableSection />
    </Stack>
  );
};
