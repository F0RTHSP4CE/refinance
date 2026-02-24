import type { Entity, Tag } from '@/types/api';

export const USER_TAG_NAMES = ['member', 'resident', 'ex-resident', 'guest'] as const;

export const SYSTEM_TAG_NAMES = [
  'hackerspace',
  'pos',
  'rent',
  'system',
  'utilities',
  'withdrawal',
  'food',
  'fee',
  'exchange',
  'donation',
  'deposit',
  'automatic',
] as const;

const USER_TAG_NAME_SET = new Set<string>(USER_TAG_NAMES);

export const normalizeTagName = (name: string): string => name.trim().toLowerCase();

export const isUserTag = (tag: Pick<Tag, 'name'>): boolean => {
  return USER_TAG_NAME_SET.has(normalizeTagName(tag.name));
};

export const hasUserTag = (entity: Pick<Entity, 'tags'>): boolean => {
  return entity.tags.some(isUserTag);
};

export const filterUserEntities = (entities: Entity[]): Entity[] => {
  return entities.filter(hasUserTag);
};

export const filterNonUserEntities = (entities: Entity[]): Entity[] => {
  return entities.filter((entity) => !hasUserTag(entity));
};

export const filterUserTagOptions = (tags: Tag[]): Tag[] => {
  return tags.filter(isUserTag);
};

export const filterEntityTagOptions = (tags: Tag[]): Tag[] => {
  return tags.filter((tag) => !isUserTag(tag));
};
