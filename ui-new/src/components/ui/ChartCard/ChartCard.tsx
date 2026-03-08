import { Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { AppCard, type AppCardProps } from '../AppCard';
import { InlineState } from '../InlineState';

type ChartCardProps = Omit<AppCardProps, 'children'> & {
  title: string;
  description?: ReactNode;
  isLoading?: boolean;
  isError?: boolean;
  hasData?: boolean;
  emptyMessage?: string;
  errorMessage?: string;
  onRetry?: () => void;
  height?: 'sm' | 'md' | 'lg';
  children: ReactNode;
};

const HEIGHT_CLASS: Record<NonNullable<ChartCardProps['height']>, string> = {
  sm: 'h-[240px]',
  md: 'h-[320px]',
  lg: 'h-[360px]',
};

export const ChartCard = ({
  title,
  description,
  isLoading = false,
  isError = false,
  hasData = true,
  emptyMessage = 'No activity in the selected range.',
  errorMessage = 'This chart could not be loaded.',
  onRetry,
  height = 'md',
  children,
  ...props
}: ChartCardProps) => {
  return (
    <AppCard {...props}>
      <Stack gap="md">
        <Stack gap={4}>
          <Text size="lg" fw={700}>
            {title}
          </Text>
          {description ? (
            <Text size="sm" className="app-muted-copy">
              {description}
            </Text>
          ) : null}
        </Stack>

        {isLoading ? (
          <InlineState kind="loading" cards={1} lines={4} />
        ) : isError ? (
          <InlineState
            kind="error"
            title="Could not load chart"
            description={errorMessage}
            onRetry={onRetry}
          />
        ) : hasData ? (
          <div className={`w-full min-h-0 ${HEIGHT_CLASS[height]}`}>{children}</div>
        ) : (
          <InlineState
            kind="empty"
            title="Nothing to show yet"
            description={emptyMessage}
          />
        )}
      </Stack>
    </AppCard>
  );
};
