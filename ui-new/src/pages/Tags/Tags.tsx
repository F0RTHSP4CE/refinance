import { useMemo, useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text, TextInput, Title } from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createTag, getTags } from '@/api/tags';
import { AppCard, DataTable, RelativeDate, TagBadge, type DataTableColumn } from '@/components/ui';
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

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Tags</Title>
          <Text c="dimmed" size="sm">
            Labels used across transactions and entities.
          </Text>
        </div>
        <Button variant="default" onClick={() => setCreateOpened(true)}>
          Add Tag
        </Button>
      </Group>

      <AppCard>
        <Stack gap="md">
          <TextInput
            label="Search"
            placeholder="Find by tag name"
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
          />

          <DataTable
            columns={columns}
            data={tags}
            emptyMessage={tagsQuery.isLoading ? 'Loading tags...' : 'No tags found.'}
          />
        </Stack>
      </AppCard>

      <Modal opened={createOpened} onClose={handleCreateClose} title="Create Tag" centered>
        <form onSubmit={(event) => void handleSubmit(onCreateTag)(event)}>
          <Stack gap="md">
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextInput
                  label="Name"
                  placeholder="tag name"
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

            {createTagMutation.isError ? (
              <Alert color="red" title="Create failed">
                {createTagMutation.error.message}
              </Alert>
            ) : null}

            <Group justify="flex-end" gap="xs">
              <Button variant="subtle" onClick={handleCreateClose}>
                Cancel
              </Button>
              <Button type="submit" variant="default" loading={createTagMutation.isPending}>
                Create Tag
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
};
