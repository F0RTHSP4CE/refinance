import { useState } from 'react';
import { Button, Group, Stack, Text } from '@mantine/core';
import { FridgePayModal, CoffeePayModal, ReimburseModal } from '@/components/PaymentModals';
import { SectionCard } from '@/components/ui';

export const FridgeCoffeeCard = () => {
  const [fridgeOpened, setFridgeOpened] = useState(false);
  const [coffeeOpened, setCoffeeOpened] = useState(false);
  const [reimburseOpened, setReimburseOpened] = useState(false);

  return (
    <>
      <SectionCard
        title="Shared supplies"
        description="Low-friction flows for kitchen stash top-ups and shared restocks."
      >
        <Stack gap="sm">
          <Text size="sm" className="app-muted-copy">
            Use these for fridge runs, coffee restocks, and reimbursement when you covered shared supplies for F0RTHSP4CE.
          </Text>

          <Group gap="xs" wrap="wrap">
            <Button variant="subtle" size="sm" onClick={() => setFridgeOpened(true)}>
              Fridge stash
            </Button>
            <Button variant="subtle" size="sm" onClick={() => setCoffeeOpened(true)}>
              Coffee stash
            </Button>
            <Button variant="subtle" size="sm" onClick={() => setReimburseOpened(true)}>
              Reimburse spend
            </Button>
          </Group>
        </Stack>
      </SectionCard>

      <FridgePayModal opened={fridgeOpened} onClose={() => setFridgeOpened(false)} />
      <CoffeePayModal opened={coffeeOpened} onClose={() => setCoffeeOpened(false)} />
      <ReimburseModal opened={reimburseOpened} onClose={() => setReimburseOpened(false)} />
    </>
  );
};
