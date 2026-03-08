import {
  EntityDirectoryPage,
  type EntityDirectoryConfig,
} from '@/components/ui/EntityDirectoryPage/EntityDirectoryPage';
import { filterEntityTagOptions, filterNonUserEntities } from '@/constants/entityTaxonomy';

const ENTITIES_CONFIG: EntityDirectoryConfig = {
  title: 'Entities',
  subtitle: 'System and operational entities without user tags.',
  addButtonLabel: 'Add Entity',
  createModalTitle: 'Create Entity',
  createSubmitLabel: 'Create Entity',
  searchPlaceholder: 'Find by name',
  tagFilterPlaceholder: 'All entity tags',
  emptyLoadingMessage: 'Loading entities...',
  emptyMessage: 'No entities found.',
  formNamePlaceholder: 'entity name',
  formTagPlaceholder: 'Select tags',
  queryScope: 'entities-page',
  filterEntities: filterNonUserEntities,
  filterTagOptions: filterEntityTagOptions,
  requireTagSelection: false,
};

export const Entities = () => {
  return <EntityDirectoryPage config={ENTITIES_CONFIG} />;
};
