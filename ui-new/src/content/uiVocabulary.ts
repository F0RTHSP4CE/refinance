export const APP_BRAND = {
  name: 'F0RTHSP4CE Finance',
  shortName: 'F0RTHSP4CE',
  logoAlt: 'F0RTHSP4CE Finance',
} as const;

export const NAV_LABELS = {
  home: 'Home',
  transactions: 'Transactions',
  fee: 'Dues',
  splits: 'Splits',
  stats: 'Stats',
  users: 'Members',
  entities: 'Entities',
  treasuries: 'Funds',
  tags: 'Labels',
} as const;

export const DIRECTORY_VOCABULARY = {
  users: {
    title: NAV_LABELS.users,
    subtitle:
      'People with member-style tags who participate in F0RTHSP4CE finances, dues, and split runs.',
    addLabel: 'Add member',
    createTitle: 'Create member',
    createSubmitLabel: 'Create member',
    searchPlaceholder: 'Find by handle or name',
    tagFilterPlaceholder: 'All member labels',
    emptyLoadingMessage: 'Loading members...',
    emptyMessage: 'No members match the current filters.',
    formNamePlaceholder: 'member name',
    formTagPlaceholder: 'Select member labels',
    listTitle: 'Member roster',
    listDescription:
      'Browse people, inspect labels, and launch money flows without dropping into a dense finance table.',
    createSubtitle:
      'Create a new member record with the labels that keep dues, splits, and money flows trustworthy.',
    createDescription:
      'Keep names and labels deliberate so this person lands in the right F0RTHSP4CE workflows.',
    searchLabel: 'Search members',
    tagsLabel: 'Member labels',
    mobileEmptyComment: 'No note yet',
    activeLabel: 'active',
    inactiveLabel: 'inactive',
  },
  entities: {
    title: NAV_LABELS.entities,
    subtitle:
      'Shared services, vendors, autonomous actors, and other non-member records used across F0RTHSP4CE finance flows.',
    addLabel: 'Add entity',
    createTitle: 'Create entity',
    createSubmitLabel: 'Create entity',
    searchPlaceholder: 'Find by handle or name',
    tagFilterPlaceholder: 'All entity labels',
    emptyLoadingMessage: 'Loading entities...',
    emptyMessage: 'No entities match the current filters.',
    formNamePlaceholder: 'entity name',
    formTagPlaceholder: 'Select entity labels',
    listTitle: 'Entity registry',
    listDescription:
      'Track shared finance entities, service accounts, vendors, and bots in the same responsive flow as the rest of the app.',
    createSubtitle:
      'Create a shared entity with the labels that keep filters, dues, and money movement readable.',
    createDescription:
      'Choose a clear name and label set so this entity lands in the right operational flows.',
    searchLabel: 'Search entities',
    tagsLabel: 'Entity labels',
    mobileEmptyComment: 'No note yet',
    activeLabel: 'active',
    inactiveLabel: 'inactive',
  },
} as const;

export const BANNED_UI_TERMS = [
  'office',
  'workspace',
  'infrastructure',
  'metadata',
  'directory record',
  'quick financial operations',
] as const;
