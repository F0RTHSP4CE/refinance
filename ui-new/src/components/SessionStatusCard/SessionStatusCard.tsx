import { Button, Group, Stack, Text } from '@mantine/core';
import { AppCard } from '@/components/ui';
import type { ActorEntity } from '@/types/api';

type SessionStatusCardProps = {
  token: string | null;
  actorEntity: ActorEntity | null;
  isLoading: boolean;
  onRefresh: () => void;
  onClear: () => void;
};

export const SessionStatusCard = ({
  token,
  actorEntity,
  isLoading,
  onRefresh,
  onClear,
}: SessionStatusCardProps) => {
  return (
    <AppCard>
      <Stack gap="xs">
        <Text fw={600}>Session status</Text>
        <Text size="sm" c="dimmed">
          {token
            ? 'Token is set in localStorage and X-Token header will be sent.'
            : 'No token set yet.'}
        </Text>
        <Text size="sm">
          Actor:{' '}
          <Text span fw={600}>
            {actorEntity?.name ?? 'Not authenticated'}
          </Text>
        </Text>
        <Group>
          <Button variant="default" onClick={onRefresh} loading={isLoading}>
            Refresh /entities/me
          </Button>
          <Button color="gray" variant="light" onClick={onClear}>
            Clear token
          </Button>
        </Group>
      </Stack>
    </AppCard>
  );
};
