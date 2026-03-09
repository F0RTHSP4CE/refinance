import { useMemo, useState } from 'react';
import { Alert, Button, Stack, Text, TextInput } from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createTag, getTags } from '@/api/tags';
import {
  DataTable,
  FilterBar,
  PageHeader,
  RelativeDate,
  TagBadge,
  AppModal,
  AppModalFooter,
  ModalStepHeader,
  SectionCard,
  type DataTableColumn,
} from '@/components/ui';
import type { Tag } from '@/types/api';

const tagCreateSchema = z.object({
  name: z.string().trim().min(1, 'Name is required'),
  comment: z.string().optional(),
});

type TagCreateFormValues = z.infer<typeof tagCreateSchema>;

const DEFAULT_FORM_VALUES: TagCreateFormValues = {
  name: '',
  comment: '',
};

const MAX_ITEMS = 500;

export const Tags = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [createOpened, setCreateOpened] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TagCreateFormValues>({
    resolver: zodResolver(tagCreateSchema),
    defaultValues: DEFAULT_FORM_VALUES,
  });

  const tagsQuery = useQuery({
    queryKey: ['tags', 'tags-page'],
    queryFn: ({ signal }) => getTags({ limit: MAX_ITEMS, signal }),
  });

  const createTagMutation = useMutation({
    mutationFn: createTag,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['tags'] }),
        queryClient.invalidateQueries({ queryKey: ['tags', 'tags-page'] }),
      ]);
      setCreateOpened(false);
      reset(DEFAULT_FORM_VALUES);
    },
  });

  const tags = useMemo(() => {
    const allTags = tagsQuery.data?.items ?? [];
    if (!search.trim()) return allTags;

    const searchLower = search.trim().toLowerCase();
    return allTags.filter((tag) => tag.name.toLowerCase().includes(searchLower));
  }, [tagsQuery.data?.items, search]);

  const columns: DataTableColumn<Tag>[] = [
    {
      key: 'name',
      label: 'Name',
      render: (tag) => <TagBadge id={tag.id} name={tag.name} />,
    },
    {
      key: 'comment',
      label: 'Comment',
      render: (tag) => <Text size="sm">{tag.comment || '—'}</Text>,
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (tag) =>
        tag.created_at ? <RelativeDate isoString={tag.created_at} /> : <Text size="sm">—</Text>,
    },
  ];

  const handleCreateClose = () => {
    setCreateOpened(false);
    reset(DEFAULT_FORM_VALUES);
  };

  const onCreateTag = (values: TagCreateFormValues) => {
    createTagMutation.mutate({
      name: values.name,
      comment: values.comment?.trim() || undefined,
    });
  };

  const resultSummary = `${tags.length} of ${tagsQuery.data?.total ?? 0} label${
    (tagsQuery.data?.total ?? 0) === 1 ? '' : 's'
  }`;

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="F0RTHSP4CE labels"
        title="Labels"
        subtitle="The shared label set used across members, actors, dues, transactions, and split runs."
        actions={
          <Button variant="default" onClick={() => setCreateOpened(true)}>
            Add label
          </Button>
        }
      />

      <FilterBar
        title="Filter labels"
        description="Search the shared label set without burying the results inside the filter card."
        resultSummary={resultSummary}
      >
        <TextInput
          label="Search"
          placeholder="Find by label name"
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
        />
      </FilterBar>

      <SectionCard
        title="Shared label set"
        description="Desktop keeps the full label table. Mobile collapses each row into a simpler card."
      >
        <DataTable
          columns={columns}
          data={tags}
          isLoading={tagsQuery.isLoading}
          loadingState={{ cards: 2, lines: 3 }}
          emptyState={{
            title: 'No labels found',
            description: 'Try a broader search or create the first shared label for the space.',
          }}
          resultSummary={resultSummary}
        />
      </SectionCard>

      <AppModal
        opened={createOpened}
        onClose={handleCreateClose}
        title="Create label"
        subtitle="Add a reusable label for members, actors, dues, transactions, and split flows."
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
                form="create-tag-form"
                variant="default"
                loading={createTagMutation.isPending}
              >
                Create label
              </Button>
            }
          />
        }
      >
        <form id="create-tag-form" onSubmit={(event) => void handleSubmit(onCreateTag)(event)}>
          <Stack gap="md">
            <ModalStepHeader
              eyebrow="Label set"
              title="Create label"
              description="Choose a short name and optional note so the label stays understandable in filters, dues, and record details."
            />
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Name"
                  placeholder="label name"
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
                  placeholder="optional note"
                  value={field.value || ''}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                />
              )}
            />

            {createTagMutation.isError ? (
              <Alert color="red" title="Create failed">
                {createTagMutation.error.message}
              </Alert>
            ) : null}
          </Stack>
        </form>
      </AppModal>
    </Stack>
  );
};
