import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useEffect, useState } from 'react';
import { z } from 'zod';
import { getEntities } from '@/api/entities';
import { addSplitParticipant, getSplit } from '@/api/splits';
import { getTags } from '@/api/tags';
import { useAuthStore } from '@/stores/auth';
import type { Split } from '@/types/api';

const participantSchema = z.object({
  entity_id: z.string().optional(),
  entity_tag_id: z.string().optional(),
  fixed_amount: z.number().positive('Fixed amount must be positive').optional(),
});

type ParticipantFormValues = z.infer<typeof participantSchema>;

type SplitParticipantModalProps = {
  opened: boolean;
  splitId: number | null;
  mode?: 'join' | 'add';
  onClose: () => void;
  onSaved?: (split: Split) => void;
};

const MAX_ITEMS = 500;

export const SplitParticipantModal = ({
  opened,
  splitId,
  mode = 'add',
  onClose,
  onSaved,
}: SplitParticipantModalProps) => {
  const queryClient = useQueryClient();
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const [selectionMode, setSelectionMode] = useState<'entity' | 'tag'>('entity');
  const activeSelectionMode = mode === 'join' ? 'entity' : selectionMode;
  const {
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<ParticipantFormValues>({
    resolver: zodResolver(participantSchema),
    defaultValues: {
      entity_id: '',
      entity_tag_id: '',
      fixed_amount: undefined,
    },
  });

  useEffect(() => {
    if (!opened) return;
    reset({
      entity_id: mode === 'join' && actorEntity ? String(actorEntity.id) : '',
      entity_tag_id: '',
      fixed_amount: undefined,
    });
  }, [actorEntity, mode, opened, reset]);

  const splitQuery = useQuery({
    queryKey: ['split', splitId, 'participant-modal'],
    queryFn: ({ signal }) => getSplit(splitId!, signal),
    enabled: opened && splitId != null,
  });

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'split-participant'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
    enabled: opened && mode === 'add',
  });

  const tagsQuery = useQuery({
    queryKey: ['tags', 'split-participant'],
    queryFn: ({ signal }) => getTags({ limit: MAX_ITEMS, signal }),
    enabled: opened && mode === 'add',
  });

  const handleClose = () => {
    setSelectionMode('entity');
    reset({
      entity_id: '',
      entity_tag_id: '',
      fixed_amount: undefined,
    });
    onClose();
  };

  const saveMutation = useMutation({
    mutationFn: async (values: ParticipantFormValues) => {
      if (splitId == null) {
        throw new Error('Split is missing.');
      }

      if (mode === 'join') {
        if (!actorEntity) {
          throw new Error('Actor entity is missing.');
        }
        return addSplitParticipant(splitId, {
          entity_id: actorEntity.id,
          fixed_amount: values.fixed_amount,
        });
      }

      if (activeSelectionMode === 'entity' && values.entity_id) {
        return addSplitParticipant(splitId, {
          entity_id: Number(values.entity_id),
          fixed_amount: values.fixed_amount,
        });
      }

      if (activeSelectionMode === 'tag' && values.entity_tag_id) {
        return addSplitParticipant(splitId, {
          entity_tag_id: Number(values.entity_tag_id),
          fixed_amount: values.fixed_amount,
        });
      }

      throw new Error(
        activeSelectionMode === 'entity' ? 'Select an entity.' : 'Select a participant tag.'
      );
    },
    onSuccess: async (updatedSplit) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['splits'] }),
        queryClient.invalidateQueries({ queryKey: ['split', updatedSplit.id] }),
      ]);
      onSaved?.(updatedSplit);
      handleClose();
    },
  });

  const entityOptions =
    entitiesQuery.data?.items
      .map((entity) => ({
        value: String(entity.id),
        label: entity.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  const tagOptions =
    tagsQuery.data?.items
      .map((tag) => ({
        value: String(tag.id),
        label: tag.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  const split = splitQuery.data ?? null;
  const currency = split?.currency.toUpperCase() ?? 'CUR';
  const fixedAmountPlaceholder = split?.share_preview.next_share ?? '';

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={mode === 'join' ? 'Join split' : 'Add participant'}
      centered
    >
      <form onSubmit={(event) => void handleSubmit((values) => saveMutation.mutate(values))(event)}>
        <Stack gap="md">
          {mode === 'join' ? (
            <TextInput label="Entity" value={actorEntity?.name ?? 'Current actor'} readOnly />
          ) : null}

          {mode === 'add' ? (
            <div>
              <Text size="sm" fw={500} mb={6}>
                Add by
              </Text>
              <SegmentedControl
                fullWidth
                value={activeSelectionMode}
                onChange={(value) => {
                  const nextMode = value === 'tag' ? 'tag' : 'entity';
                  setSelectionMode(nextMode);
                  setValue('entity_id', '');
                  setValue('entity_tag_id', '');
                }}
                data={[
                  { label: 'Entity', value: 'entity' },
                  { label: 'Tag', value: 'tag' },
                ]}
              />
            </div>
          ) : null}

          {mode === 'add' && activeSelectionMode === 'entity' ? (
            <Controller
              name="entity_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="Entity"
                  placeholder="Select participant"
                  searchable
                  data={entityOptions}
                  value={field.value}
                  onChange={(value) => {
                    setValue('entity_tag_id', '');
                    field.onChange(value);
                  }}
                  error={errors.entity_id?.message}
                />
              )}
            />
          ) : null}

          {mode === 'add' && activeSelectionMode === 'tag' ? (
            <Controller
              name="entity_tag_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="Entity tag"
                  placeholder="Add all matching entities"
                  searchable
                  data={tagOptions}
                  value={field.value}
                  onChange={(value) => {
                    setValue('entity_id', '');
                    field.onChange(value);
                  }}
                  error={errors.entity_tag_id?.message}
                />
              )}
            />
          ) : null}

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Controller
              name="fixed_amount"
              control={control}
              render={({ field }) => (
                <NumberInput
                  label="Amount"
                  description="Leave empty for equal split of the remaining amount"
                  min={0.01}
                  step={0.01}
                  decimalScale={2}
                  placeholder={fixedAmountPlaceholder}
                  value={field.value}
                  onChange={(value) =>
                    field.onChange(typeof value === 'number' ? value : undefined)
                  }
                  error={errors.fixed_amount?.message}
                />
              )}
            />
            <TextInput label="Currency" value={currency} readOnly />
          </SimpleGrid>

          {saveMutation.isError ? (
            <Alert color="red" title="Could not add participant">
              {saveMutation.error.message}
            </Alert>
          ) : null}

          <Group justify="flex-end">
            <Button variant="subtle" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" variant="default" loading={saveMutation.isPending}>
              {mode === 'join' ? 'Join' : 'Add participant'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
