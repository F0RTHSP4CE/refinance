import { IconCalendarStats } from '@tabler/icons-react';
import { MonthPickerInput, type MonthPickerInputProps } from '@mantine/dates';
import {
  APP_COMBOBOX_PROPS,
  APP_DATE_INPUT_CLASSNAMES,
  APP_DATE_DROPDOWN_STYLES,
  APP_INPUT_STYLES,
  formatIsoMonthValue,
  mergeClassNames,
  parseIsoMonthValue,
} from '../sharedInputStyles';

type AppMonthFieldProps = Omit<MonthPickerInputProps<'default'>, 'value' | 'onChange'> & {
  value?: string | null;
  onChange?: (value: string) => void;
};

export const AppMonthField = ({
  value,
  onChange,
  styles,
  classNames,
  popoverProps,
  size = 'md',
  radius = 'md',
  valueFormat = 'MMMM YYYY',
  clearable = true,
  ...props
}: AppMonthFieldProps) => {
  return (
    <MonthPickerInput<'default'>
      value={parseIsoMonthValue(value)}
      onChange={(nextValue) => onChange?.(formatIsoMonthValue(nextValue))}
      size={size}
      radius={radius}
      clearable={clearable}
      valueFormat={valueFormat}
      leftSection={<IconCalendarStats size={16} />}
      styles={{ ...APP_INPUT_STYLES, ...APP_DATE_DROPDOWN_STYLES, ...styles }}
      classNames={mergeClassNames(APP_DATE_INPUT_CLASSNAMES, classNames)}
      popoverProps={{ ...APP_COMBOBOX_PROPS, ...popoverProps }}
      {...props}
    />
  );
};
