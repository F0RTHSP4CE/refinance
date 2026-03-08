import { IconCalendar } from '@tabler/icons-react';
import { DatePickerInput, type DatePickerInputProps } from '@mantine/dates';
import {
  APP_COMBOBOX_PROPS,
  APP_DATE_INPUT_CLASSNAMES,
  APP_DATE_DROPDOWN_STYLES,
  APP_INPUT_STYLES,
  formatIsoDateValue,
  mergeClassNames,
  parseIsoDateValue,
} from '../sharedInputStyles';

type AppDateFieldProps = Omit<DatePickerInputProps<'default'>, 'value' | 'onChange'> & {
  value?: string | null;
  onChange?: (value: string) => void;
};

export const AppDateField = ({
  value,
  onChange,
  styles,
  classNames,
  popoverProps,
  size = 'md',
  radius = 'md',
  valueFormat = 'D MMM YYYY',
  clearable = true,
  ...props
}: AppDateFieldProps) => {
  return (
    <DatePickerInput<'default'>
      value={parseIsoDateValue(value)}
      onChange={(nextValue) => onChange?.(formatIsoDateValue(nextValue))}
      size={size}
      radius={radius}
      clearable={clearable}
      valueFormat={valueFormat}
      leftSection={<IconCalendar size={16} />}
      styles={{ ...APP_INPUT_STYLES, ...APP_DATE_DROPDOWN_STYLES, ...styles }}
      classNames={mergeClassNames(APP_DATE_INPUT_CLASSNAMES, classNames)}
      popoverProps={{ ...APP_COMBOBOX_PROPS, ...popoverProps }}
      {...props}
    />
  );
};
