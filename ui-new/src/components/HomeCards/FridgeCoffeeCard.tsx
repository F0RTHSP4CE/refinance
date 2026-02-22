import { useState } from 'react';
import { Button, Card, Group, Stack, Text } from '@mantine/core';
import { FridgePayModal, CoffeePayModal, ReimburseModal } from '@/components/PaymentModals';

export const FridgeCoffeeCard = () => {
  const [fridgeOpened, setFridgeOpened] = useState(false);
  const [coffeeOpened, setCoffeeOpened] = useState(false);
  const [reimburseOpened, setReimburseOpened] = useState(false);

  return (
    <>
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Text size="lg" fw={700}>
            Fridge &amp; Coffee Machine
          </Text>

          <Text size="sm" c="dimmed">
            Pay for drinks, snacks and coffee.
            <br />
            Get paid when you refill them.
          </Text>

          <Group gap="xs" grow>
            <Button variant="default" onClick={() => setFridgeOpened(true)}>
              Pay Fridge
            </Button>
            <Button variant="default" onClick={() => setCoffeeOpened(true)}>
              Pay Coffee Machine
            </Button>
            <Button variant="default" onClick={() => setReimburseOpened(true)}>
              Reimburse
            </Button>
          </Group>
        </Stack>
      </Card>

      <FridgePayModal opened={fridgeOpened} onClose={() => setFridgeOpened(false)} />
      <CoffeePayModal opened={coffeeOpened} onClose={() => setCoffeeOpened(false)} />
      <ReimburseModal opened={reimburseOpened} onClose={() => setReimburseOpened(false)} />
    </>
  );
};
