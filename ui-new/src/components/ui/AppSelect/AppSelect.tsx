import { Select, type SelectProps } from '@mantine/core';
import {
  APP_COMBOBOX_PROPS,
  APP_INPUT_CLASSNAMES,
  APP_INPUT_STYLES,
  mergeClassNames,
} from '../sharedInputStyles';

export const AppSelect = ({
  styles,
  classNames,
  comboboxProps,
  size = 'md',
  radius = 'md',
  ...props
}: SelectProps) => {
  return (
    <Select
      size={size}
      radius={radius}
      styles={{ ...APP_INPUT_STYLES, ...styles }}
      classNames={mergeClassNames(APP_INPUT_CLASSNAMES, classNames)}
      comboboxProps={{ ...APP_COMBOBOX_PROPS, ...comboboxProps }}
      {...props}
    />
  );
};
