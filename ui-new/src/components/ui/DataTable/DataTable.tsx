import { ScrollArea, Table } from '@mantine/core';
import type { ReactNode } from 'react';

export type DataTableColumn<T> = {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  data: T[];
  emptyMessage?: string;
};

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = 'No data.',
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={col.key}>{col.label}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          <Table.Tr>
            <Table.Td colSpan={columns.length} style={{ textAlign: 'center', color: 'var(--mantine-color-dimmed)' }}>
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
              <Table.Th key={col.key}>{col.label}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((row, idx) => (
            <Table.Tr key={(row.id as number) ?? idx}>
              {columns.map((col) => (
                <Table.Td key={col.key}>
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
