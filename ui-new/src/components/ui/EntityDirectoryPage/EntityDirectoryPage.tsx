import { useMemo, useState } from 'react';
import { Anchor, Alert, Button, Group, Stack, Text, TextInput } from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { createEntity, getEntities } from '@/api/entities';
import { getTags } from '@/api/tags';
import { EntityEditModal } from '@/components/EntityEditModal/EntityEditModal';
import {
  MoneyActionModal,
  type MoneyActionMode,
} from '@/components/MoneyActionModal/MoneyActionModal';
import { useAuthStore } from '@/stores/auth';
import type { Entity, Tag } from '@/types/api';
import { AppModal, AppModalFooter } from '../AppModal';
import { AppMultiSelect } from '../AppMultiSelect';
import { DataTable, type DataTableColumn } from '../DataTable';
import { FilterBar } from '../FilterBar';
import { ModalStepHeader } from '../ModalStepHeader';
import { PageHeader } from '../PageHeader';
import { RelativeDate } from '../RelativeDate';
import { SectionCard } from '../SectionCard';
import { StatusBadge } from '../StatusBadge';
import { TagList } from '../TagList';

export type EntityDirectoryConfig = {
  labels: {
    singular: string;
    plural: string;
    searchLabel: string;
    tagsLabel: string;
    activeLabel: string;
    inactiveLabel: string;
    emptyComment: string;
  };
  copy: {
    eyebrow: string;
    subtitle: string;
    addButtonLabel: string;
    createTitle: string;
    createSubmitLabel: string;
    createSubtitle: string;
    createDescription: string;
    searchPlaceholder: string;
    tagFilterPlaceholder: string;
    emptyLoadingMessage: string;
    emptyMessage: string;
    formNamePlaceholder: string;
    formTagPlaceholder: string;
    listTitle: string;
    listDescription: string;
  };
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
        <StatusBadge tone={entity.active ? 'success' : 'danger'}>
          {entity.active ? config.labels.activeLabel : config.labels.inactiveLabel}
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
      <PageHeader
        eyebrow={config.copy.eyebrow}
        title={config.labels.plural}
        subtitle={config.copy.subtitle}
        actions={
          <Button variant="default" onClick={() => setCreateOpened(true)}>
            {config.copy.addButtonLabel}
          </Button>
        }
      />

      <FilterBar
        title="Filters"
        description={`Search by name or narrow the ${config.labels.plural.toLowerCase()} list by shared labels.`}
        resultSummary={`${entities.length} ${config.labels.plural.toLowerCase()} visible`}
      >
        <Stack gap="md">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <TextInput
              label={config.labels.searchLabel}
              placeholder={config.copy.searchPlaceholder}
              value={search}
              onChange={(event) => setSearch(event.currentTarget.value)}
            />
            <AppMultiSelect
              label={config.labels.tagsLabel}
              placeholder={config.copy.tagFilterPlaceholder}
              data={selectableTags}
              searchable
              clearable
              value={selectedTagIds}
              onChange={setSelectedTagIds}
              nothingFoundMessage={tagsQuery.isLoading ? 'Loading labels...' : 'No labels found'}
            />
          </div>
        </Stack>
      </FilterBar>

      <SectionCard
        title={config.copy.listTitle}
        description={config.copy.listDescription}
      >
        <Stack gap="md">
          <DataTable
            columns={columns}
            data={entities}
            isLoading={entitiesQuery.isLoading}
            emptyState={{
              title: 'Nothing matches right now',
              description: config.copy.emptyMessage,
            }}
            resultSummary={`${entities.length} ${config.labels.plural.toLowerCase()} in view`}
            emptyMessage={
              entitiesQuery.isLoading ? config.copy.emptyLoadingMessage : config.copy.emptyMessage
            }
            renderMobileTitle={(entity) => (
              <Anchor component={Link} to={`/profile/${entity.id}`} underline="hover" fw={600}>
                {entity.name}
              </Anchor>
            )}
            renderMobileSubtitle={(entity) => entity.comment || config.labels.emptyComment}
            renderMobileAside={(entity) => (
              <StatusBadge tone={entity.active ? 'success' : 'danger'} size="sm">
                {entity.active ? config.labels.activeLabel : config.labels.inactiveLabel}
              </StatusBadge>
            )}
            renderMobileDetails={(entity) => [
              {
                label: 'Tags',
                value: entity.tags.length ? <TagList tags={entity.tags} mode="compact" /> : '—',
              },
              {
                label: 'Created',
                value: <RelativeDate isoString={entity.created_at} />,
              },
            ]}
            renderMobileFooter={(entity) => {
              const isSelf = actorEntity?.id === entity.id;
              return (
                <Group gap="xs" wrap="wrap">
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
                  <Button variant="outline" size="xs" onClick={() => setEditingEntity(entity)}>
                    Edit
                  </Button>
                </Group>
              );
            }}
          />
        </Stack>
      </SectionCard>

      <AppModal
        opened={createOpened}
        onClose={handleCreateClose}
        title={config.copy.createTitle}
        subtitle={config.copy.createSubtitle}
        footer={
          <AppModalFooter
            secondary={
              <Button variant="subtle" onClick={handleCreateClose}>
                Cancel
              </Button>
            }
            primary={
              <Button
                type="submit"
                form={`entity-create-${config.queryScope}`}
                variant="default"
                loading={createEntityMutation.isPending}
              >
                {config.copy.createSubmitLabel}
              </Button>
            }
          />
        }
      >
        <form
          id={`entity-create-${config.queryScope}`}
          onSubmit={(event) => void handleSubmit(onCreateEntity)(event)}
        >
          <Stack gap="md">
            <ModalStepHeader
              eyebrow={config.copy.eyebrow}
              title={config.copy.createTitle}
              description={config.copy.createDescription}
            />
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Name"
                  placeholder={config.copy.formNamePlaceholder}
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
                <AppMultiSelect
                  label="Labels"
                  placeholder={config.copy.formTagPlaceholder}
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
          </Stack>
        </form>
      </AppModal>

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
