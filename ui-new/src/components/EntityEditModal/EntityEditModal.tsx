import { Alert, Button, Group, Modal, MultiSelect, Stack, Switch, TextInput } from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useEffect } from 'react';
import { z } from 'zod';
import { updateEntity } from '@/api/entities';
import type { Entity } from '@/types/api';

const entityEditSchema = z.object({
  name: z.string().trim().min(1, 'Name is required'),
  comment: z.string().optional(),
  active: z.boolean(),
  tag_ids: z.array(z.string()),
});

type EntityEditFormValues = z.infer<typeof entityEditSchema>;

type EntityEditModalProps = {
  opened: boolean;
  entity: Entity | null;
  tagOptions: { value: string; label: string }[];
  requireTagSelection?: boolean;
  onClose: () => void;
};

const getDefaultValues = (entity: Entity | null): EntityEditFormValues => ({
  name: entity?.name ?? '',
  comment: entity?.comment ?? '',
  active: entity?.active ?? true,
  tag_ids: entity?.tags.map((tag) => String(tag.id)) ?? [],
});

export const EntityEditModal = ({
  opened,
  entity,
  tagOptions,
  requireTagSelection = false,
  onClose,
}: EntityEditModalProps) => {
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm<EntityEditFormValues>({
    resolver: zodResolver(entityEditSchema),
    defaultValues: getDefaultValues(entity),
  });

  useEffect(() => {
    if (!opened) return;
    reset(getDefaultValues(entity));
  }, [entity, opened, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: EntityEditFormValues) => {
      if (!entity) {
        throw new Error('Entity is missing.');
      }

      if (requireTagSelection && values.tag_ids.length === 0) {
        setError('tag_ids', { type: 'manual', message: 'Select at least one tag.' });
        throw new Error('Select at least one tag.');
      }

      clearErrors('tag_ids');

      return updateEntity(entity.id, {
        name: values.name.trim(),
        comment: values.comment?.trim() || undefined,
        active: values.active,
        tag_ids: values.tag_ids.map((tagId) => Number(tagId)),
      });
    },
    onSuccess: async (savedEntity) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['entities'] }),
        queryClient.invalidateQueries({ queryKey: ['entities', savedEntity.id] }),
      ]);
      onClose();
    },
  });

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={entity ? `Edit ${entity.name}` : 'Edit entity'}
      centered
    >
      <form
        onSubmit={(event) => void handleSubmit((values) => updateMutation.mutate(values))(event)}
      >
        <Stack gap="md">
          <Controller
            name="name"
            control={control}
            render={({ field }) => (
              <TextInput
                label="Name"
                placeholder="Entity name"
                value={field.value}
                onChange={field.onChange}
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
                placeholder="Optional note"
                value={field.value || ''}
                onChange={field.onChange}
              />
            )}
          />

          <Controller
            name="tag_ids"
            control={control}
            render={({ field }) => (
              <MultiSelect
                label="Tags"
                placeholder="Select tags"
                data={tagOptions}
                searchable
                clearable={!requireTagSelection}
                value={field.value}
                onChange={field.onChange}
                error={errors.tag_ids?.message}
              />
            )}
          />

          <Controller
            name="active"
            control={control}
            render={({ field }) => (
              <Switch
                checked={field.value}
                onChange={(event) => field.onChange(event.currentTarget.checked)}
                label="Entity is active"
              />
            )}
          />

          {updateMutation.isError ? (
            <Alert color="red" title="Could not save entity">
              {updateMutation.error.message}
            </Alert>
          ) : null}

          <Group justify="flex-end">
            <Button variant="subtle" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="default" loading={updateMutation.isPending}>
              Save changes
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
