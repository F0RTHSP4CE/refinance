import { SegmentedControl, type SegmentedControlProps } from '@mantine/core';
import {
  APP_SEGMENTED_CONTROL_CLASSNAMES,
  APP_SEGMENTED_CONTROL_STYLES,
  mergeClassNames,
} from '../sharedInputStyles';

export const AppSegmentedControl = ({
  styles,
  classNames,
  radius = 'md',
  ...props
}: SegmentedControlProps) => {
  return (
    <SegmentedControl
      radius={radius}
      styles={{ ...APP_SEGMENTED_CONTROL_STYLES, ...styles }}
      classNames={mergeClassNames(APP_SEGMENTED_CONTROL_CLASSNAMES, classNames)}
      {...props}
    />
  );
};
