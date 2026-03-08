import { ScrollArea, Table } from '@mantine/core';
import type { CSSProperties, KeyboardEvent, ReactNode } from 'react';

export type DataTableColumn<T> = {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
  headerStyle?: CSSProperties;
  cellStyle?: CSSProperties;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  data: T[];
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  getRowAriaLabel?: (row: T) => string;
  getRowStyle?: (row: T) => CSSProperties | undefined;
};

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = 'No data.',
  onRowClick,
  getRowAriaLabel,
  getRowStyle,
}: DataTableProps<T>) {
  const handleRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!onRowClick) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onRowClick(row);
    }
  };

  if (data.length === 0) {
    return (
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={col.key} style={col.headerStyle}>
                {col.label}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          <Table.Tr>
            <Table.Td
              colSpan={columns.length}
              style={{ textAlign: 'center', color: 'var(--mantine-color-dimmed)' }}
            >
              {emptyMessage}
            </Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>
    );
  }

  return (
    <ScrollArea>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={col.key} style={col.headerStyle}>
                {col.label}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((row, idx) => (
            <Table.Tr
              key={(row.id as number) ?? idx}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={onRowClick ? (event) => handleRowKeyDown(event, row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              role={onRowClick ? 'button' : undefined}
              aria-label={onRowClick ? (getRowAriaLabel?.(row) ?? 'Open row details') : undefined}
              style={{
                ...(onRowClick ? { cursor: 'pointer' } : {}),
                ...(getRowStyle?.(row) ?? {}),
              }}
            >
              {columns.map((col) => (
                <Table.Td key={col.key} style={col.cellStyle}>
                  {col.render ? col.render(row) : String((row[col.key] ?? '') as string)}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
}
