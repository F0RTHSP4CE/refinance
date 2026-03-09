import type {
  MultiSelectProps,
  SelectProps,
  SegmentedControlProps,
  TabsProps,
} from '@mantine/core';
import type {
  DatePickerInputProps,
  MonthPickerInputProps,
} from '@mantine/dates';

export const APP_INPUT_STYLES = {
  label: {
    color: 'var(--app-text-secondary)',
    fontSize: '0.82rem',
    fontWeight: 700,
    letterSpacing: '0.02em',
    marginBottom: '0.35rem',
  },
  input: {
    background: 'var(--app-control-surface)',
    border: '1px solid var(--app-control-border)',
    color: 'var(--app-text-primary)',
    borderRadius: '0.9rem',
    minHeight: '2.8rem',
    boxShadow: 'var(--app-control-shadow)',
    transition:
      'border-color 160ms ease, box-shadow 160ms ease, background 160ms ease',
  },
  wrapper: {
    gap: '0.35rem',
  },
  section: {
    color: 'var(--app-text-muted)',
  },
  dropdown: {
    background: 'var(--app-panel-surface-strong)',
    border: '1px solid var(--app-panel-border)',
    boxShadow: 'var(--app-panel-shadow)',
    backdropFilter: 'blur(12px)',
    borderRadius: '1rem',
    padding: '0.35rem',
  },
  option: {
    borderRadius: '0.8rem',
    color: 'var(--app-text-primary)',
    minHeight: '2.45rem',
    paddingBlock: '0.55rem',
    paddingInline: '0.8rem',
  },
  description: {
    color: 'var(--app-text-muted)',
  },
} as const;

export const APP_MULTISELECT_STYLES = {
  ...APP_INPUT_STYLES,
  pill: {
    background: 'rgba(155, 227, 65, 0.12)',
    color: 'var(--app-accent)',
    border: '1px solid rgba(155, 227, 65, 0.22)',
  },
  pillsList: {
    gap: '0.35rem',
  },
} as const;

export const APP_DATE_DROPDOWN_STYLES = {
  dropdown: {
    background: 'var(--app-panel-surface-strong)',
    border: '1px solid var(--app-panel-border)',
    boxShadow: 'var(--app-panel-shadow)',
    backdropFilter: 'blur(12px)',
    borderRadius: '1rem',
  },
  calendarHeader: {
    marginBottom: '0.35rem',
  },
  calendarHeaderLevel: {
    color: 'var(--app-text-primary)',
    fontWeight: 700,
  },
  calendarHeaderControl: {
    color: 'var(--app-text-secondary)',
    borderRadius: '0.75rem',
  },
  weekday: {
    color: 'var(--app-text-muted)',
  },
  day: {
    color: 'var(--app-text-primary)',
    borderRadius: '0.75rem',
  },
  month: {
    color: 'var(--app-text-primary)',
    borderRadius: '0.75rem',
  },
  monthCell: {
    padding: '0.2rem',
  },
  dayCell: {
    padding: '0.12rem',
  },
} as const;

export const APP_COMBOBOX_PROPS = {
  withinPortal: true,
} as const;

export const APP_SEGMENTED_CONTROL_STYLES = {
  root: {
    padding: '0.25rem',
    borderRadius: '0.95rem',
    background: 'var(--app-panel-surface-strong)',
    border: '1px solid var(--app-panel-border)',
    boxShadow: 'var(--app-control-shadow)',
  },
  control: {
    borderRadius: '0.8rem',
    transition: 'opacity 160ms ease, transform 160ms ease',
  },
  indicator: {
    borderRadius: '0.75rem',
    background:
      'linear-gradient(180deg, rgba(11, 15, 20, 0.98), rgba(7, 10, 14, 0.98))',
    border: '1px solid rgba(155, 227, 65, 0.16)',
    boxShadow:
      '0 10px 20px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
  },
  label: {
    color: 'rgba(174, 185, 200, 0.8)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    minHeight: '2.35rem',
    paddingInline: '0.85rem',
    transition: 'color 160ms ease',
  },
  innerLabel: {
    display: 'flex',
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    zIndex: 1,
    fontWeight: 700,
    color: 'inherit',
  },
} as const;

export const APP_INPUT_CLASSNAMES = {
  wrapper: 'app-input-wrapper',
  label: 'app-input-label',
  input: 'app-input-field',
  section: 'app-input-section',
  dropdown: 'app-input-dropdown',
  option: 'app-input-option',
  description: 'app-input-description',
} as const;

export const APP_MULTISELECT_CLASSNAMES = {
  ...APP_INPUT_CLASSNAMES,
  pill: 'app-multiselect-pill',
  pillsList: 'app-multiselect-pills-list',
} as const;

export const APP_DATE_INPUT_CLASSNAMES = {
  ...APP_INPUT_CLASSNAMES,
  dropdown: 'app-date-dropdown',
  calendarHeader: 'app-date-calendar-header',
  calendarHeaderLevel: 'app-date-calendar-header-level',
  calendarHeaderControl: 'app-date-calendar-header-control',
  weekday: 'app-date-weekday',
  day: 'app-date-day',
  month: 'app-date-month',
  monthCell: 'app-date-month-cell',
  dayCell: 'app-date-day-cell',
} as const;

export const APP_TABS_CLASSNAMES = {
  list: 'app-tabs-list',
  tab: 'app-tabs-tab',
  tabLabel: 'app-tabs-tab-label',
  panel: 'app-tabs-panel',
} as const;

export const APP_SEGMENTED_CONTROL_CLASSNAMES = {
  root: 'app-segmented-control',
  control: 'app-segmented-control-control',
  label: 'app-segmented-control-label',
  indicator: 'app-segmented-control-indicator',
  innerLabel: 'app-segmented-control-inner-label',
} as const;

const pad = (value: number) => String(value).padStart(2, '0');

export const parseIsoDateValue = (value?: string | null): Date | null => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) return null;
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }
  return parsed;
};

export const formatIsoDateValue = (value: Date | string | null): string => {
  if (!value) return '';
  if (typeof value === 'string') {
    const parsed =
      parseIsoDateValue(value) ??
      (() => {
        const next = new Date(value);
        return Number.isNaN(next.getTime()) ? null : next;
      })();
    return parsed ? formatIsoDateValue(parsed) : value;
  }
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
};

export const parseIsoMonthValue = (value?: string | null): Date | null => {
  if (!value || !/^\d{4}-\d{2}$/.test(value)) return null;
  const [year, month] = value.split('-').map(Number);
  if (!year || !month) return null;
  const parsed = new Date(year, month - 1, 1);
  if (parsed.getFullYear() !== year || parsed.getMonth() !== month - 1) {
    return null;
  }
  return parsed;
};

export const formatIsoMonthValue = (value: Date | string | null): string => {
  if (!value) return '';
  if (typeof value === 'string') {
    const parsed =
      parseIsoMonthValue(value) ??
      (() => {
        const next = new Date(value);
        return Number.isNaN(next.getTime()) ? null : next;
      })();
    return parsed ? formatIsoMonthValue(parsed) : value;
  }
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}`;
};

export const isClassNamesRecord = <T extends string>(
  classNames?: Partial<Record<T, string>> | ((...args: never[]) => Partial<Record<T, string>>)
): classNames is Partial<Record<T, string>> =>
  classNames != null && typeof classNames !== 'function';

export const mergeClassNames = <T extends string>(
  base: Partial<Record<T, string>>,
  classNames?: Partial<Record<T, string>> | ((...args: never[]) => Partial<Record<T, string>>)
): Partial<Record<T, string>> => {
  if (!isClassNamesRecord(classNames)) {
    return base;
  }

  const keys = new Set([...Object.keys(base), ...Object.keys(classNames)]);
  return Array.from(keys).reduce<Partial<Record<T, string>>>((acc, key) => {
    const typedKey = key as T;
    acc[typedKey] = [base[typedKey], classNames[typedKey]].filter(Boolean).join(' ');
    return acc;
  }, {});
};

export type AppInputStyles = typeof APP_INPUT_STYLES;
export type AppInputClassNames = typeof APP_INPUT_CLASSNAMES;
export type AppMultiSelectStyles = typeof APP_MULTISELECT_STYLES;
export type AppDateStyles = typeof APP_DATE_DROPDOWN_STYLES;
export type AppDateClassNames = typeof APP_DATE_INPUT_CLASSNAMES;
export type AppSegmentedControlStyles = typeof APP_SEGMENTED_CONTROL_STYLES;
export type AppTabsClassNames = typeof APP_TABS_CLASSNAMES;
export type SelectClassNamesProp = SelectProps['classNames'];
export type MultiSelectClassNamesProp = MultiSelectProps['classNames'];
export type DatePickerClassNamesProp = DatePickerInputProps<'default'>['classNames'];
export type MonthPickerClassNamesProp = MonthPickerInputProps<'default'>['classNames'];
export type SegmentedControlClassNamesProp = SegmentedControlProps['classNames'];
export type TabsClassNamesProp = TabsProps['classNames'];
