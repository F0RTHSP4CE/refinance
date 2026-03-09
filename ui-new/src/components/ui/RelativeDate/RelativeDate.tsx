import { Text, Tooltip } from '@mantine/core';
import { formatDateTime, formatRelativeDate } from '@/utils/date';

type RelativeDateProps = {
  isoString: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
};

export const RelativeDate = ({ isoString, size = 'sm' }: RelativeDateProps) => (
  <Tooltip label={formatDateTime(isoString)}>
    <Text size={size} component="span">
      {formatRelativeDate(isoString)}
    </Text>
  </Tooltip>
);
