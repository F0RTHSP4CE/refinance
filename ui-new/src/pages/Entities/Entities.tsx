import {
  EntityDirectoryPage,
  type EntityDirectoryConfig,
} from '@/components/ui/EntityDirectoryPage/EntityDirectoryPage';
import { filterEntityTagOptions, filterNonUserEntities } from '@/constants/entityTaxonomy';
import { DIRECTORY_VOCABULARY } from '@/content/uiVocabulary';

const vocabulary = DIRECTORY_VOCABULARY.entities;

const ENTITIES_CONFIG: EntityDirectoryConfig = {
  labels: {
    singular: 'entity',
    plural: vocabulary.title,
    searchLabel: vocabulary.searchLabel,
    tagsLabel: vocabulary.tagsLabel,
    activeLabel: vocabulary.activeLabel,
    inactiveLabel: vocabulary.inactiveLabel,
    emptyComment: vocabulary.mobileEmptyComment,
  },
  copy: {
    eyebrow: 'F0RTHSP4CE Finance',
    subtitle: vocabulary.subtitle,
    addButtonLabel: vocabulary.addLabel,
    createTitle: vocabulary.createTitle,
    createSubmitLabel: vocabulary.createSubmitLabel,
    createSubtitle: vocabulary.createSubtitle,
    createDescription: vocabulary.createDescription,
    searchPlaceholder: vocabulary.searchPlaceholder,
    tagFilterPlaceholder: vocabulary.tagFilterPlaceholder,
    emptyLoadingMessage: vocabulary.emptyLoadingMessage,
    emptyMessage: vocabulary.emptyMessage,
    formNamePlaceholder: vocabulary.formNamePlaceholder,
    formTagPlaceholder: vocabulary.formTagPlaceholder,
    listTitle: vocabulary.listTitle,
    listDescription: vocabulary.listDescription,
  },
  queryScope: 'entities-page',
  filterEntities: filterNonUserEntities,
  filterTagOptions: filterEntityTagOptions,
  requireTagSelection: false,
};

export const Entities = () => {
  return <EntityDirectoryPage config={ENTITIES_CONFIG} />;
};
