import { EntityDirectoryPage, type EntityDirectoryConfig } from '@/components/ui';
import { filterUserEntities, filterUserTagOptions } from '@/constants/entityTaxonomy';

const USERS_CONFIG: EntityDirectoryConfig = {
  title: 'Users',
  subtitle: 'Member-like entities with user tags.',
  addButtonLabel: 'Add User',
  createModalTitle: 'Create User',
  createSubmitLabel: 'Create User',
  searchPlaceholder: 'Find by name',
  tagFilterPlaceholder: 'All user tags',
  emptyLoadingMessage: 'Loading users...',
  emptyMessage: 'No users found.',
  formNamePlaceholder: 'user name',
  formTagPlaceholder: 'Select user tags',
  queryScope: 'users-page',
  filterEntities: filterUserEntities,
  filterTagOptions: filterUserTagOptions,
  requireTagSelection: true,
};

export const Users = () => {
  return <EntityDirectoryPage config={USERS_CONFIG} />;
};
