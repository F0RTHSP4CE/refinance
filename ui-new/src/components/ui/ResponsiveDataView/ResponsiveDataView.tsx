import { Box, Group, ScrollArea, Stack, Table, Text, UnstyledButton } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import type { CSSProperties, KeyboardEvent, ReactNode } from 'react';
import { AppCard } from '../AppCard';
import { EmptyState } from '../EmptyState';
import { InlineState } from '../InlineState';

export type ResponsiveDataColumn<T> = {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
  headerStyle?: CSSProperties;
  cellStyle?: CSSProperties;
  mobileLabel?: string;
  mobileRender?: (row: T) => ReactNode;
  mobileHidden?: boolean;
};

type ResponsiveDataDetail = {
  label: string;
  value: ReactNode;
};

export type ResponsiveDataViewProps<T> = {
  columns: ResponsiveDataColumn<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
  emptyState?: {
    title: string;
    description?: ReactNode;
    action?: ReactNode;
  };
  loadingState?: {
    cards?: number;
    lines?: number;
  };
  resultSummary?: ReactNode;
  onRowClick?: (row: T) => void;
  getRowAriaLabel?: (row: T) => string;
  getRowStyle?: (row: T) => CSSProperties | undefined;
  getRowKey?: (row: T, index: number) => string | number;
  renderMobileTitle?: (row: T) => ReactNode;
  renderMobileSubtitle?: (row: T) => ReactNode;
  renderMobileAside?: (row: T) => ReactNode;
  renderMobileDetails?: (row: T) => ResponsiveDataDetail[];
  renderMobileFooter?: (row: T) => ReactNode;
};

const getCellContent = <T extends Record<string, unknown>>(column: ResponsiveDataColumn<T>, row: T) =>
  column.render ? column.render(row) : String((row[column.key] ?? '') as string);

export function ResponsiveDataView<T extends Record<string, unknown>>({
  columns,
  data,
  isLoading = false,
  emptyMessage = 'No data.',
  emptyState,
  loadingState,
  resultSummary,
  onRowClick,
  getRowAriaLabel,
  getRowStyle,
  getRowKey,
  renderMobileTitle,
  renderMobileSubtitle,
  renderMobileAside,
  renderMobileDetails,
  renderMobileFooter,
}: ResponsiveDataViewProps<T>) {
  const isDesktop = useMediaQuery('(min-width: 48em)', true, {
    getInitialValueInEffect: false,
  });

  const handleRowKeyDown = (event: KeyboardEvent<HTMLElement>, row: T) => {
    if (!onRowClick) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onRowClick(row);
    }
  };

  if (isLoading) {
    return (
      <InlineState
        kind="loading"
        cards={loadingState?.cards ?? 1}
        lines={loadingState?.lines ?? 4}
      />
    );
  }

  if (data.length === 0) {
    return (
      <EmptyState
        compact
        title={emptyState?.title ?? emptyMessage}
        description={
          emptyState?.description ?? 'Try adjusting filters or create a new item from the page actions.'
        }
        action={emptyState?.action}
      />
    );
  }

  if (isDesktop) {
    return (
      <Stack gap="sm">
        {resultSummary ? <Box className="app-muted-copy">{resultSummary}</Box> : null}
        <ScrollArea>
          <Table
            highlightOnHover
            withColumnBorders={false}
            style={{
              minWidth: '100%',
            }}
          >
            <Table.Thead>
              <Table.Tr>
                {columns.map((col) => (
                  <Table.Th
                    key={col.key}
                    style={{
                      color: 'var(--app-text-muted)',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      borderBottom: '1px solid var(--app-border-subtle)',
                      paddingTop: '0.85rem',
                      paddingBottom: '0.85rem',
                      ...col.headerStyle,
                    }}
                  >
                    {col.label}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.map((row, idx) => (
                <Table.Tr
                  key={getRowKey ? getRowKey(row, idx) : ((row.id as number | undefined) ?? idx)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onKeyDown={onRowClick ? (event) => handleRowKeyDown(event, row) : undefined}
                  tabIndex={onRowClick ? 0 : undefined}
                  role={onRowClick ? 'button' : undefined}
                  aria-label={onRowClick ? (getRowAriaLabel?.(row) ?? 'Open row details') : undefined}
                  style={{
                    cursor: onRowClick ? 'pointer' : undefined,
                    transition: 'background-color 160ms ease',
                    ...getRowStyle?.(row),
                  }}
                >
                  {columns.map((col) => (
                    <Table.Td
                      key={col.key}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                        paddingTop: '0.85rem',
                        paddingBottom: '0.85rem',
                        verticalAlign: 'top',
                        ...col.cellStyle,
                      }}
                    >
                      {getCellContent(col, row)}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Stack>
    );
  }

  return (
    <Stack gap="sm">
      {resultSummary ? <Box className="app-muted-copy">{resultSummary}</Box> : null}
      {data.map((row, idx) => {
        const visibleColumns = columns.filter((column) => !column.mobileHidden);
        const title =
          renderMobileTitle?.(row) ?? getCellContent(visibleColumns[0] ?? columns[0], row);
        const subtitle =
          renderMobileSubtitle?.(row) ??
          (visibleColumns[1] ? getCellContent(visibleColumns[1], row) : null);
        const details =
          renderMobileDetails?.(row) ??
          visibleColumns.slice(1).map((column) => ({
            label: column.mobileLabel ?? column.label,
            value: column.mobileRender ? column.mobileRender(row) : getCellContent(column, row),
          }));
        const content = (
          <AppCard p="md" style={{ ...getRowStyle?.(row) }}>
            <Stack gap="sm">
              <Group justify="space-between" align="start" gap="sm" wrap="nowrap">
                <Stack gap={4} style={{ minWidth: 0 }}>
                  <Box component="div" style={{ wordBreak: 'break-word', fontWeight: 700 }}>
                    {title}
                  </Box>
                  {subtitle ? (
                    <Box component="div" style={{ fontSize: '0.92rem' }} className="app-muted-copy">
                      {subtitle}
                    </Box>
                  ) : null}
                </Stack>
                {renderMobileAside ? renderMobileAside(row) : null}
              </Group>

              <Stack gap={8}>
                {details.map((detail) => (
                  <Group key={detail.label} justify="space-between" align="start" gap="md">
                    <Text size="xs" fw={700} tt="uppercase" className="app-muted-copy">
                      {detail.label}
                    </Text>
                    <Box
                      component="div"
                      style={{
                        flex: 1,
                        wordBreak: 'break-word',
                        textAlign: 'right',
                        fontSize: '0.92rem',
                      }}
                    >
                      {detail.value}
                    </Box>
                  </Group>
                ))}
              </Stack>

              {renderMobileFooter ? renderMobileFooter(row) : null}
            </Stack>
          </AppCard>
        );

        if (!onRowClick) {
          return (
            <div key={getRowKey ? getRowKey(row, idx) : ((row.id as number | undefined) ?? idx)}>
              {content}
            </div>
          );
        }

        return (
          <UnstyledButton
            key={getRowKey ? getRowKey(row, idx) : ((row.id as number | undefined) ?? idx)}
            onClick={() => onRowClick(row)}
            onKeyDown={(event) => handleRowKeyDown(event, row)}
            aria-label={getRowAriaLabel?.(row) ?? 'Open row details'}
          >
            {content}
          </UnstyledButton>
        );
      })}
    </Stack>
  );
}
