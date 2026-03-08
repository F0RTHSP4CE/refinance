import { Stack } from '@mantine/core';
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

      <div className="app-page-grid lg:grid-cols-[minmax(0,1.42fr)_minmax(18.5rem,0.84fr)] lg:items-start">
        <BalanceCard />
        <Stack gap="md">
          <FeeInvoicesStatusCard />
          <DraftsCard />
          <FridgeCoffeeCard />
        </Stack>
      </div>

      <HomeTransactionsTableSection />
    </Stack>
  );
};
