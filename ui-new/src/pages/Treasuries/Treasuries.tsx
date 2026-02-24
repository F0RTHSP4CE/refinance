import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { IconCircleCheck, IconCircleX } from '@tabler/icons-react';
import { createTreasury, getTreasuries, updateTreasury, type Treasury } from '@/api/treasuries';
import { getEntities } from '@/api/entities';
import { AppCard, DataTable, RelativeDate, type DataTableColumn } from '@/components/ui';

const treasuryFormSchema = z.object({
  name: z.string().trim().min(1, 'Name is required'),
  comment: z.string().optional(),
  active: z.boolean(),
  author_entity_id: z.string().nullable().optional(),
});

type TreasuryFormValues = z.infer<typeof treasuryFormSchema>;

type ActiveFilter = 'all' | 'active' | 'inactive';

const DEFAULT_CREATE_VALUES: TreasuryFormValues = {
  name: '',
  comment: '',
  active: true,
  author_entity_id: null,
};

const MAX_ITEMS = 500;

const balanceToNumber = (value: string): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const Treasuries = () => {
  const queryClient = useQueryClient();
  const [nameFilter, setNameFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>('all');
  const [editorOpened, setEditorOpened] = useState(false);
  const [editingTreasury, setEditingTreasury] = useState<Treasury | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TreasuryFormValues>({
    resolver: zodResolver(treasuryFormSchema),
    defaultValues: DEFAULT_CREATE_VALUES,
  });

  const activeParam = useMemo(() => {
    if (activeFilter === 'all') return undefined;
    return activeFilter === 'active';
  }, [activeFilter]);

  const treasuriesQuery = useQuery({
    queryKey: ['treasuries', nameFilter, activeFilter],
    queryFn: ({ signal }) =>
      getTreasuries({
        name: nameFilter.trim() || undefined,
        active: activeParam,
        limit: MAX_ITEMS,
        signal,
      }),
  });

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'treasuries-page'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
  });

  const closeEditor = () => {
    setEditorOpened(false);
    setEditingTreasury(null);
    reset(DEFAULT_CREATE_VALUES);
  };

  const invalidateTreasuries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['treasuries'] }),
      queryClient.invalidateQueries({ queryKey: ['treasuries', nameFilter, activeFilter] }),
    ]);
  };

  const createTreasuryMutation = useMutation({
    mutationFn: createTreasury,
    onSuccess: async () => {
      await invalidateTreasuries();
      closeEditor();
    },
  });

  const updateTreasuryMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateTreasury>[1] }) =>
      updateTreasury(id, data),
    onSuccess: async () => {
      await invalidateTreasuries();
      closeEditor();
    },
  });

  const authorOptions = useMemo(() => {
    const entities = entitiesQuery.data?.items ?? [];
    return entities
      .map((entity) => ({
        value: String(entity.id),
        label: entity.name,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [entitiesQuery.data?.items]);

  const openCreateEditor = () => {
    setEditingTreasury(null);
    reset(DEFAULT_CREATE_VALUES);
    setEditorOpened(true);
  };

  const openEditEditor = (treasury: Treasury) => {
    setEditingTreasury(treasury);
    reset({
      name: treasury.name,
      comment: treasury.comment || '',
      active: treasury.active,
      author_entity_id: treasury.author_entity_id ? String(treasury.author_entity_id) : null,
    });
    setEditorOpened(true);
  };

  const mutationError = createTreasuryMutation.error || updateTreasuryMutation.error;
  const isSubmitting = createTreasuryMutation.isPending || updateTreasuryMutation.isPending;

  const onSubmitTreasury = (values: TreasuryFormValues) => {
    const payload = {
      name: values.name,
      comment: values.comment?.trim() || undefined,
      active: values.active,
      author_entity_id: values.author_entity_id ? Number(values.author_entity_id) : null,
    };

    if (editingTreasury) {
      updateTreasuryMutation.mutate({ id: editingTreasury.id, data: payload });
      return;
    }

    createTreasuryMutation.mutate(payload);
  };

  const renderBalances = (treasury: Treasury) => {
    const balances = treasury.balances;
    if (!balances) return <Text size="sm">—</Text>;

    const completedEntries = Object.entries(balances.completed).filter(
      ([, amount]) => balanceToNumber(amount) !== 0
    );
    const draftEntries = Object.entries(balances.draft).filter(
      ([, amount]) => balanceToNumber(amount) !== 0
    );

    if (completedEntries.length === 0 && draftEntries.length === 0) {
      return <Text size="sm">—</Text>;
    }

    return (
      <Stack gap={2}>
        {completedEntries.map(([currency, amount]) => (
          <Text key={`completed-${currency}`} size="sm">
            {amount} {currency.toUpperCase()}
          </Text>
        ))}
        {draftEntries.map(([currency, amount]) => (
          <Text key={`draft-${currency}`} size="sm" c="dimmed">
            {amount} {currency.toUpperCase()}*
          </Text>
        ))}
      </Stack>
    );
  };

  const columns: DataTableColumn<Treasury>[] = [
    {
      key: 'name',
      label: 'Name',
      render: (treasury) => <Text fw={600}>{treasury.name}</Text>,
    },
    {
      key: 'author',
      label: 'Author',
      render: (treasury) => <Text size="sm">{treasury.author_entity?.name || '—'}</Text>,
    },
    {
      key: 'balances',
      label: 'Balances',
      render: renderBalances,
    },
    {
      key: 'comment',
      label: 'Comment',
      render: (treasury) => <Text size="sm">{treasury.comment || '—'}</Text>,
    },
    {
      key: 'active',
      label: 'Active',
      render: (treasury) => (
        <Badge
          variant="filled"
          style={
            treasury.active
              ? {
                  backgroundColor: 'var(--mantine-color-black)',
                  color: 'var(--mantine-color-white)',
                  border: '1px solid var(--mantine-color-black)',
                }
              : {
                  backgroundColor: 'var(--mantine-color-white)',
                  color: 'var(--mantine-color-black)',
                  border: '1px solid var(--mantine-color-black)',
                }
          }
        >
          {treasury.active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (treasury) => <RelativeDate isoString={treasury.created_at} />,
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (treasury) => (
        <Button variant="subtle" size="xs" onClick={() => openEditEditor(treasury)}>
          Edit
        </Button>
      ),
    },
  ];

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Treasuries</Title>
          <Text c="dimmed" size="sm">
            Managed balances with optional author ownership.
          </Text>
        </div>
        <Button variant="default" onClick={openCreateEditor}>
          Add Treasury
        </Button>
      </Group>

      <AppCard>
        <Stack gap="md">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,9fr)_minmax(8.75rem,1fr)]">
            <TextInput
              label="Search"
              placeholder="Filter by name"
              value={nameFilter}
              onChange={(event) => setNameFilter(event.currentTarget.value)}
            />

            <Select
              label="Status"
              value={activeFilter}
              onChange={(value) => setActiveFilter((value as ActiveFilter) || 'all')}
              data={[
                { value: 'all', label: 'All' },
                { value: 'active', label: 'Active' },
                { value: 'inactive', label: 'Inactive' },
              ]}
              allowDeselect={false}
            />
          </div>

          <DataTable
            columns={columns}
            data={treasuriesQuery.data?.items ?? []}
            emptyMessage={
              treasuriesQuery.isLoading ? 'Loading treasuries...' : 'No treasuries found.'
            }
          />
        </Stack>
      </AppCard>

      <Modal
        opened={editorOpened}
        onClose={closeEditor}
        title={editingTreasury ? 'Edit Treasury' : 'Create Treasury'}
        centered
      >
        <form onSubmit={(event) => void handleSubmit(onSubmitTreasury)(event)}>
          <Stack gap="md">
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Name"
                  placeholder="treasury name"
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  error={errors.name?.message}
                />
              )}
            />

            <Controller
              name="comment"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Comment"
                  placeholder="optional"
                  value={field.value || ''}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            <Controller
              name="author_entity_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="Author"
                  placeholder="Select author entity"
                  data={authorOptions}
                  searchable
                  clearable
                  value={field.value || null}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  nothingFoundMessage={entitiesQuery.isLoading ? 'Loading...' : 'No entities found'}
                />
              )}
            />

            <Controller
              name="active"
              control={control}
              render={({ field }) => (
                <Stack gap={6}>
                  <Text fw={500} size="sm">
                    Status
                  </Text>
                  <Group grow>
                    <Button
                      type="button"
                      variant={field.value ? 'filled' : 'default'}
                      style={
                        field.value
                          ? {
                              backgroundColor: 'var(--mantine-color-black)',
                              color: 'var(--mantine-color-white)',
                              border: '1px solid var(--mantine-color-black)',
                            }
                          : {
                              backgroundColor: 'transparent',
                              color: 'var(--mantine-color-dimmed)',
                              border: '1px solid var(--mantine-color-dark-3)',
                            }
                      }
                      leftSection={<IconCircleCheck size={16} />}
                      onClick={() => field.onChange(true)}
                    >
                      Active
                    </Button>
                    <Button
                      type="button"
                      variant={field.value ? 'default' : 'filled'}
                      style={
                        field.value
                          ? {
                              backgroundColor: 'transparent',
                              color: 'var(--mantine-color-dimmed)',
                              border: '1px solid var(--mantine-color-dark-3)',
                            }
                          : {
                              backgroundColor: 'var(--mantine-color-white)',
                              color: 'var(--mantine-color-black)',
                              border: '1px solid var(--mantine-color-black)',
                            }
                      }
                      leftSection={<IconCircleX size={16} />}
                      onClick={() => field.onChange(false)}
                    >
                      Inactive
                    </Button>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {field.value
                      ? 'Treasury is enabled and available for operations.'
                      : 'Treasury is disabled for new operations.'}
                  </Text>
                </Stack>
              )}
            />

            {mutationError ? (
              <Alert color="red" title="Save failed">
                {mutationError.message}
              </Alert>
            ) : null}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={closeEditor}>
                Cancel
              </Button>
              <Button type="submit" variant="default" loading={isSubmitting}>
                {editingTreasury ? 'Save Changes' : 'Create Treasury'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
};
