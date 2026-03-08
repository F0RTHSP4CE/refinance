import {
  Button,
  Group,
  NumberInput,
  Pagination,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getEntities } from '@/api/entities';
import { getSplits } from '@/api/splits';
import {
  SplitDetailsModal,
  SplitEditorModal,
  SplitParticipantModal,
  SplitSummaryCard,
} from '@/components/Splits';
import { AccentSurface, AppCard } from '@/components/ui';
import { CURRENCIES } from '@/constants/entities';

type SplitSearchFormState = {
  actor_entity_id: string;
  recipient_entity_id: string;
  amount_min: string;
  amount_max: string;
  currency: string;
  comment: string;
  performed: string;
};

const DEFAULT_LIMIT = 20;
const MAX_ITEMS = 500;

const DEFAULT_FORM_STATE: SplitSearchFormState = {
  actor_entity_id: '',
  recipient_entity_id: '',
  amount_min: '',
  amount_max: '',
  currency: '',
  comment: '',
  performed: '',
};

const getSearchFormState = (searchParams: URLSearchParams): SplitSearchFormState => ({
  actor_entity_id: searchParams.get('actor_entity_id') ?? '',
  recipient_entity_id: searchParams.get('recipient_entity_id') ?? '',
  amount_min: searchParams.get('amount_min') ?? '',
  amount_max: searchParams.get('amount_max') ?? '',
  currency: searchParams.get('currency') ?? '',
  comment: searchParams.get('comment') ?? '',
  performed: searchParams.get('performed') ?? '',
});

const parseOptionalNumber = (value: string) => {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

export const Splits = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [createOpened, setCreateOpened] = useState(false);
  const [selectedSplitId, setSelectedSplitId] = useState<number | null>(null);
  const [joinSplitId, setJoinSplitId] = useState<number | null>(null);

  const searchParamsKey = searchParams.toString();
  const appliedFilters = useMemo(() => getSearchFormState(searchParams), [searchParams]);
  const [searchForm, setSearchForm] = useState<SplitSearchFormState>(appliedFilters);

  useEffect(() => {
    setSearchForm(appliedFilters);
  }, [appliedFilters]);

  const page = Math.max(1, Number(searchParams.get('page') || '1'));
  const limit = Math.max(1, Number(searchParams.get('limit') || String(DEFAULT_LIMIT)));

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'splits-page'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
  });

  const splitsQuery = useQuery({
    queryKey: ['splits', searchParamsKey],
    queryFn: ({ signal }) =>
      getSplits({
        actor_entity_id: appliedFilters.actor_entity_id
          ? Number(appliedFilters.actor_entity_id)
          : undefined,
        recipient_entity_id: appliedFilters.recipient_entity_id
          ? Number(appliedFilters.recipient_entity_id)
          : undefined,
        amount_min: parseOptionalNumber(appliedFilters.amount_min),
        amount_max: parseOptionalNumber(appliedFilters.amount_max),
        currency: appliedFilters.currency || undefined,
        comment: appliedFilters.comment.trim() || undefined,
        performed:
          appliedFilters.performed === 'true'
            ? true
            : appliedFilters.performed === 'false'
              ? false
              : undefined,
        skip: (page - 1) * limit,
        limit,
        signal,
      }),
  });

  const entityOptions =
    entitiesQuery.data?.items
      .map((entity) => ({
        value: String(entity.id),
        label: entity.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  const splits = splitsQuery.data?.items ?? [];
  const total = splitsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const activeSplits = splits.filter((split) => !split.performed);
  const completedSplits = splits.filter((split) => split.performed);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = new URLSearchParams();
    next.set('page', '1');
    next.set('limit', String(limit || DEFAULT_LIMIT));

    if (searchForm.actor_entity_id) next.set('actor_entity_id', searchForm.actor_entity_id);
    if (searchForm.recipient_entity_id) {
      next.set('recipient_entity_id', searchForm.recipient_entity_id);
    }
    if (searchForm.amount_min.trim()) next.set('amount_min', searchForm.amount_min.trim());
    if (searchForm.amount_max.trim()) next.set('amount_max', searchForm.amount_max.trim());
    if (searchForm.currency) next.set('currency', searchForm.currency);
    if (searchForm.comment.trim()) next.set('comment', searchForm.comment.trim());
    if (searchForm.performed) next.set('performed', searchForm.performed);

    setSearchParams(next);
  };

  const resetSearch = () => {
    setSearchForm(DEFAULT_FORM_STATE);
    setSearchParams(
      new URLSearchParams({
        page: '1',
        limit: String(DEFAULT_LIMIT),
      })
    );
  };

  const handlePageChange = (nextPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(nextPage));
    next.set('limit', String(limit));
    setSearchParams(next);
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Splits</Title>
          <Text c="dimmed" size="sm">
            Create resident collections, track participation, and perform the resulting transfers
            from one place.
          </Text>
        </div>
        <Button variant="default" onClick={() => setCreateOpened(true)}>
          Create split
        </Button>
      </Group>

      <AccentSurface>
        <Stack gap="md">
          <div>
            <Text fw={700}>How splits work</Text>
            <Text size="sm" c="dimmed">
              You define the recipient and total amount, participants join, and performing the split
              creates completed transactions for each participant share.
            </Text>
          </div>

          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
            <AppCard p="md">
              <Stack gap={4}>
                <Text fw={600}>1. Create</Text>
                <Text size="sm" c="dimmed">
                  Name the split, choose who receives the money, and set the total amount.
                </Text>
              </Stack>
            </AppCard>
            <AppCard p="md">
              <Stack gap={4}>
                <Text fw={600}>2. Gather participants</Text>
                <Text size="sm" c="dimmed">
                  People can join directly, or you can add a participant or tag-based group.
                </Text>
              </Stack>
            </AppCard>
            <AppCard p="md">
              <Stack gap={4}>
                <Text fw={600}>3. Perform</Text>
                <Text size="sm" c="dimmed">
                  Once the list looks right, perform the split to generate the transactions.
                </Text>
              </Stack>
            </AppCard>
          </SimpleGrid>
        </Stack>
      </AccentSurface>

      <AppCard>
        <form onSubmit={submitSearch}>
          <Stack gap="md">
            <Group justify="space-between" align="center">
              <Text fw={600}>Split filters</Text>
              <Text size="sm" c="dimmed">
                {total} result{total === 1 ? '' : 's'}
              </Text>
            </Group>

            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
              <Select
                label="Actor"
                placeholder="Any actor"
                searchable
                clearable
                data={entityOptions}
                value={searchForm.actor_entity_id || null}
                onChange={(value) =>
                  setSearchForm((current) => ({ ...current, actor_entity_id: value ?? '' }))
                }
              />
              <Select
                label="Recipient"
                placeholder="Any recipient"
                searchable
                clearable
                data={entityOptions}
                value={searchForm.recipient_entity_id || null}
                onChange={(value) =>
                  setSearchForm((current) => ({
                    ...current,
                    recipient_entity_id: value ?? '',
                  }))
                }
              />
              <Select
                label="Currency"
                clearable
                data={CURRENCIES.map((currency) => ({ value: currency, label: currency }))}
                value={searchForm.currency || null}
                onChange={(value) =>
                  setSearchForm((current) => ({ ...current, currency: value ?? '' }))
                }
              />
              <NumberInput
                label="Minimum amount"
                min={0}
                placeholder="10.00"
                value={searchForm.amount_min}
                onChange={(value) =>
                  setSearchForm((current) => ({
                    ...current,
                    amount_min:
                      typeof value === 'number' && Number.isFinite(value) ? String(value) : '',
                  }))
                }
              />
              <NumberInput
                label="Maximum amount"
                min={0}
                placeholder="20.00"
                value={searchForm.amount_max}
                onChange={(value) =>
                  setSearchForm((current) => ({
                    ...current,
                    amount_max:
                      typeof value === 'number' && Number.isFinite(value) ? String(value) : '',
                  }))
                }
              />
              <Select
                label="Status"
                clearable
                data={[
                  { value: 'false', label: 'Active' },
                  { value: 'true', label: 'Completed' },
                ]}
                value={searchForm.performed || null}
                onChange={(value) =>
                  setSearchForm((current) => ({ ...current, performed: value ?? '' }))
                }
              />
            </SimpleGrid>

            <TextInput
              label="Name"
              placeholder="Search by split name"
              value={searchForm.comment}
              onChange={(event) =>
                setSearchForm((current) => ({ ...current, comment: event.currentTarget.value }))
              }
            />

            <Group justify="flex-end">
              <Button type="button" variant="subtle" onClick={resetSearch}>
                Reset
              </Button>
              <Button type="submit" variant="default">
                Apply filters
              </Button>
            </Group>
          </Stack>
        </form>
      </AppCard>

      {splitsQuery.isLoading ? (
        <Text c="dimmed">Loading splits...</Text>
      ) : splits.length === 0 ? (
        <AppCard>
          <Text c="dimmed">No splits found for the selected filters.</Text>
        </AppCard>
      ) : (
        <>
          {activeSplits.length ? (
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <Text size="lg" fw={600}>
                  Active
                </Text>
                <Text size="sm" c="dimmed">
                  Open splits waiting for participants or execution
                </Text>
              </Group>

              <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
                {activeSplits.map((split) => (
                  <SplitSummaryCard
                    key={split.id}
                    split={split}
                    onOpen={setSelectedSplitId}
                    onJoin={setJoinSplitId}
                  />
                ))}
              </SimpleGrid>
            </Stack>
          ) : null}

          {completedSplits.length ? (
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <Text size="lg" fw={600}>
                  Completed
                </Text>
                <Text size="sm" c="dimmed">
                  Finished splits with generated transactions
                </Text>
              </Group>

              <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
                {completedSplits.map((split) => (
                  <SplitSummaryCard
                    key={split.id}
                    split={split}
                    onOpen={setSelectedSplitId}
                    onJoin={setJoinSplitId}
                  />
                ))}
              </SimpleGrid>
            </Stack>
          ) : null}

          {totalPages > 1 ? (
            <Group justify="center">
              <Pagination total={totalPages} value={page} onChange={handlePageChange} />
            </Group>
          ) : null}
        </>
      )}

      <SplitEditorModal opened={createOpened} onClose={() => setCreateOpened(false)} />

      <SplitParticipantModal
        opened={joinSplitId != null}
        splitId={joinSplitId}
        mode="join"
        onClose={() => setJoinSplitId(null)}
      />

      <SplitDetailsModal
        opened={selectedSplitId != null}
        splitId={selectedSplitId}
        onClose={() => setSelectedSplitId(null)}
        onDeleted={() => setSelectedSplitId(null)}
      />
    </Stack>
  );
};
