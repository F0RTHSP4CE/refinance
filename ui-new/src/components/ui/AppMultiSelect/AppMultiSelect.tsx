import { MultiSelect, type MultiSelectProps } from '@mantine/core';
import {
  APP_COMBOBOX_PROPS,
  APP_MULTISELECT_CLASSNAMES,
  APP_MULTISELECT_STYLES,
  mergeClassNames,
} from '../sharedInputStyles';

export const AppMultiSelect = ({
  styles,
  classNames,
  comboboxProps,
  size = 'md',
  radius = 'md',
  ...props
}: MultiSelectProps) => {
  return (
    <MultiSelect
      size={size}
      radius={radius}
      styles={{ ...APP_MULTISELECT_STYLES, ...styles }}
      classNames={mergeClassNames(APP_MULTISELECT_CLASSNAMES, classNames)}
      comboboxProps={{ ...APP_COMBOBOX_PROPS, ...comboboxProps }}
      {...props}
    />
  );
};
