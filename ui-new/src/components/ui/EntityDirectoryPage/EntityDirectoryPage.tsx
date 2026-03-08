import { useMemo, useState } from 'react';
import {
  Alert,
  Anchor,
  Button,
  Group,
  Modal,
  MultiSelect,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { createEntity, getEntities } from '@/api/entities';
import { getTags } from '@/api/tags';
import { EntityEditModal } from '@/components/EntityEditModal';
import {
  MoneyActionModal,
  type MoneyActionMode,
} from '@/components/MoneyActionModal/MoneyActionModal';
import { useAuthStore } from '@/stores/auth';
import type { Entity, Tag } from '@/types/api';
import { AccentSurface } from '../AccentSurface';
import { AppCard } from '../AppCard';
import { DataTable, type DataTableColumn } from '../DataTable';
import { RelativeDate } from '../RelativeDate';
import { StatusBadge } from '../StatusBadge';
import { TagList } from '../TagList';

export type EntityDirectoryConfig = {
  title: string;
  subtitle: string;
  addButtonLabel: string;
  createModalTitle: string;
  createSubmitLabel: string;
  searchPlaceholder: string;
  tagFilterPlaceholder: string;
  emptyLoadingMessage: string;
  emptyMessage: string;
  formNamePlaceholder: string;
  formTagPlaceholder: string;
  queryScope: string;
  filterEntities: (entities: Entity[]) => Entity[];
  filterTagOptions: (tags: Tag[]) => Tag[];
  requireTagSelection: boolean;
};

type EntityDirectoryPageProps = {
  config: EntityDirectoryConfig;
};

type EntityCreateFormValues = {
  name: string;
  comment?: string;
  tag_ids: string[];
};

const DEFAULT_FORM_VALUES: EntityCreateFormValues = {
  name: '',
  comment: '',
  tag_ids: [],
};

const MAX_ITEMS = 500;

const getCreateEntitySchema = (requireTagSelection: boolean) => {
  return z.object({
    name: z.string().trim().min(1, 'Name is required'),
    comment: z.string().optional(),
    tag_ids: requireTagSelection
      ? z.array(z.string()).min(1, 'Select at least one tag')
      : z.array(z.string()),
  });
};

export const EntityDirectoryPage = ({ config }: EntityDirectoryPageProps) => {
  const queryClient = useQueryClient();
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const [search, setSearch] = useState('');
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [createOpened, setCreateOpened] = useState(false);
  const [editingEntity, setEditingEntity] = useState<Entity | null>(null);
  const [moneyAction, setMoneyAction] = useState<{
    mode: MoneyActionMode;
    entity: Entity;
  } | null>(null);

  const createSchema = useMemo(() => {
    return getCreateEntitySchema(config.requireTagSelection);
  }, [config.requireTagSelection]);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EntityCreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: DEFAULT_FORM_VALUES,
  });

  const entitiesQuery = useQuery({
    queryKey: ['entities', config.queryScope],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
  });

  const tagsQuery = useQuery({
    queryKey: ['tags', config.queryScope],
    queryFn: ({ signal }) => getTags({ limit: MAX_ITEMS, signal }),
  });

  const createEntityMutation = useMutation({
    mutationFn: createEntity,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['entities'] }),
        queryClient.invalidateQueries({ queryKey: ['entities', config.queryScope] }),
      ]);
      setCreateOpened(false);
      reset(DEFAULT_FORM_VALUES);
    },
  });

  const entities = useMemo(() => {
    const allEntities = entitiesQuery.data?.items ?? [];
    const selectedTagSet = new Set(selectedTagIds.map((id) => Number(id)));
    let filtered = config.filterEntities(allEntities);

    if (search.trim()) {
      const searchLower = search.trim().toLowerCase();
      filtered = filtered.filter((entity) => entity.name.toLowerCase().includes(searchLower));
    }

    if (selectedTagSet.size > 0) {
      filtered = filtered.filter((entity) => {
        return entity.tags.some((tag) => selectedTagSet.has(tag.id));
      });
    }

    return filtered;
  }, [config, entitiesQuery.data?.items, search, selectedTagIds]);

  const selectableTags = useMemo(() => {
    const tags = tagsQuery.data?.items ?? [];
    return config.filterTagOptions(tags).map((tag) => ({
      value: String(tag.id),
      label: tag.name,
    }));
  }, [config, tagsQuery.data?.items]);

  const columns: DataTableColumn<Entity>[] = [
    {
      key: 'name',
      label: 'Name',
      render: (entity) => (
        <Anchor component={Link} to={`/profile/${entity.id}`} underline="hover" fw={600}>
          {entity.name}
        </Anchor>
      ),
    },
    {
      key: 'tags',
      label: 'Tags',
      render: (entity) =>
        entity.tags.length ? (
          <TagList tags={entity.tags} mode="compact" />
        ) : (
          <Text size="sm">—</Text>
        ),
    },
    {
      key: 'comment',
      label: 'Comment',
      render: (entity) => <Text size="sm">{entity.comment || '—'}</Text>,
    },
    {
      key: 'active',
      label: 'Active',
      render: (entity) => (
        <StatusBadge tone={entity.active ? 'positive' : 'neutral'}>
          {entity.active ? 'Active' : 'Inactive'}
        </StatusBadge>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (entity) => <RelativeDate isoString={entity.created_at} />,
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (entity) => {
        const isSelf = actorEntity?.id === entity.id;
        return (
          <Group gap="xs" wrap="nowrap">
            <Button
              variant="subtle"
              size="xs"
              onClick={() =>
                setMoneyAction({
                  mode: 'transfer',
                  entity,
                })
              }
              disabled={!actorEntity || isSelf}
            >
              Transfer
            </Button>
            <Button
              variant="subtle"
              size="xs"
              onClick={() =>
                setMoneyAction({
                  mode: 'request',
                  entity,
                })
              }
              disabled={!actorEntity || isSelf}
            >
              Request
            </Button>
            <Button variant="subtle" size="xs" onClick={() => setEditingEntity(entity)}>
              Edit
            </Button>
          </Group>
        );
      },
    },
  ];

  const handleCreateClose = () => {
    setCreateOpened(false);
    reset(DEFAULT_FORM_VALUES);
  };

  const onCreateEntity = (values: EntityCreateFormValues) => {
    createEntityMutation.mutate({
      name: values.name,
      comment: values.comment?.trim() || undefined,
      tag_ids: values.tag_ids.map((id) => Number(id)),
    });
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>{config.title}</Title>
          <Text c="dimmed" size="sm">
            {config.subtitle}
          </Text>
        </div>
        <Button variant="default" onClick={() => setCreateOpened(true)}>
          {config.addButtonLabel}
        </Button>
      </Group>

      <AccentSurface>
        <Stack gap="md">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <TextInput
              label="Search"
              placeholder={config.searchPlaceholder}
              value={search}
              onChange={(event) => setSearch(event.currentTarget.value)}
            />
            <MultiSelect
              label="Tags filter"
              placeholder={config.tagFilterPlaceholder}
              data={selectableTags}
              searchable
              clearable
              value={selectedTagIds}
              onChange={setSelectedTagIds}
              nothingFoundMessage={tagsQuery.isLoading ? 'Loading...' : 'No tags found'}
            />
          </div>
        </Stack>
      </AccentSurface>

      <AppCard>
        <Stack gap="md">
          <DataTable
            columns={columns}
            data={entities}
            emptyMessage={
              entitiesQuery.isLoading ? config.emptyLoadingMessage : config.emptyMessage
            }
          />
        </Stack>
      </AppCard>

      <Modal
        opened={createOpened}
        onClose={handleCreateClose}
        title={config.createModalTitle}
        centered
      >
        <form onSubmit={(event) => void handleSubmit(onCreateEntity)(event)}>
          <Stack gap="md">
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Name"
                  placeholder={config.formNamePlaceholder}
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
              name="tag_ids"
              control={control}
              render={({ field }) => (
                <MultiSelect
                  label="Tags"
                  placeholder={config.formTagPlaceholder}
                  data={selectableTags}
                  searchable
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  error={errors.tag_ids?.message}
                />
              )}
            />

            {createEntityMutation.isError ? (
              <Alert color="red" title="Create failed">
                {createEntityMutation.error.message}
              </Alert>
            ) : null}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={handleCreateClose}>
                Cancel
              </Button>
              <Button type="submit" variant="default" loading={createEntityMutation.isPending}>
                {config.createSubmitLabel}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <EntityEditModal
        opened={editingEntity != null}
        entity={editingEntity}
        tagOptions={selectableTags}
        requireTagSelection={config.requireTagSelection}
        onClose={() => setEditingEntity(null)}
      />

      <MoneyActionModal
        opened={moneyAction != null}
        mode={moneyAction?.mode ?? 'transfer'}
        onClose={() => setMoneyAction(null)}
        initialFromEntityId={
          moneyAction?.mode === 'transfer' ? actorEntity?.id : moneyAction?.entity.id
        }
        initialToEntityId={
          moneyAction?.mode === 'request' ? actorEntity?.id : moneyAction?.entity.id
        }
        title={
          moneyAction
            ? moneyAction.mode === 'transfer'
              ? `Transfer with ${moneyAction.entity.name}`
              : `Request from ${moneyAction.entity.name}`
            : undefined
        }
      />
    </Stack>
  );
};
