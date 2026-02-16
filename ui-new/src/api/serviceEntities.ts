import { getEntities, getEntity } from './entities';
import type { Entity } from '@/types/api';

const SERVICE_ENTITY_ALIASES = {
  fridge: ['fridge'],
  coffee: ['coffee machine', 'coffee'],
} as const;

const SERVICE_ENTITY_FALLBACK_IDS = {
  fridge: 141,
  coffee: 150,
} as const;

const normalize = (value: string) => value.trim().toLowerCase();

const pickEntityIdByAliases = (
  entities: Entity[],
  aliases: readonly string[]
): number | null => {
  const normalizedAliases = aliases.map(normalize);
  const normalizedEntities = entities.map((entity) => ({
    ...entity,
    normalizedName: normalize(entity.name),
  }));

  const exactMatch = normalizedEntities.find((entity) =>
    normalizedAliases.includes(entity.normalizedName)
  );
  if (exactMatch) return exactMatch.id;

  const startsWithMatch = normalizedEntities.find((entity) =>
    normalizedAliases.some((alias) => entity.normalizedName.startsWith(alias))
  );
  if (startsWithMatch) return startsWithMatch.id;

  const containsMatch = normalizedEntities.find((entity) =>
    normalizedAliases.some((alias) => entity.normalizedName.includes(alias))
  );
  if (containsMatch) return containsMatch.id;

  return null;
};

export type ServiceEntityIds = {
  fridge: number;
  coffee: number;
};

const getEntitiesByAliases = async (
  aliases: readonly string[],
  signal?: AbortSignal
): Promise<Entity[]> => {
  try {
    const responses = await Promise.all(
      aliases.map((alias) =>
        getEntities({
          name: alias,
          limit: 100,
          signal,
        })
      )
    );

    const entitiesById = new Map<number, Entity>();
    for (const response of responses) {
      for (const entity of response.items) {
        entitiesById.set(entity.id, entity);
      }
    }
    return Array.from(entitiesById.values());
  } catch {
    return [];
  }
};

const getEntityByIdSafe = async (id: number, signal?: AbortSignal): Promise<Entity | null> => {
  try {
    return await getEntity(id, signal);
  } catch {
    return null;
  }
};

export const getServiceEntityIds = async (signal?: AbortSignal): Promise<ServiceEntityIds> => {
  try {
    const [fridgeEntities, coffeeEntities, fridgeFallback, coffeeFallback] =
      await Promise.all([
        getEntitiesByAliases(SERVICE_ENTITY_ALIASES.fridge, signal),
        getEntitiesByAliases(SERVICE_ENTITY_ALIASES.coffee, signal),
        getEntityByIdSafe(SERVICE_ENTITY_FALLBACK_IDS.fridge, signal),
        getEntityByIdSafe(SERVICE_ENTITY_FALLBACK_IDS.coffee, signal),
      ]);

    return {
      fridge:
        pickEntityIdByAliases(fridgeEntities, SERVICE_ENTITY_ALIASES.fridge) ??
        fridgeFallback?.id ??
        SERVICE_ENTITY_FALLBACK_IDS.fridge,
      coffee:
        pickEntityIdByAliases(coffeeEntities, SERVICE_ENTITY_ALIASES.coffee) ??
        coffeeFallback?.id ??
        SERVICE_ENTITY_FALLBACK_IDS.coffee,
    };
  } catch {
    return {
      fridge: SERVICE_ENTITY_FALLBACK_IDS.fridge,
      coffee: SERVICE_ENTITY_FALLBACK_IDS.coffee,
    };
  }
};

