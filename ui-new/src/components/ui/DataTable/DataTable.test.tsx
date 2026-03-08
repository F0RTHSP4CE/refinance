import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { DataTable, type DataTableColumn } from './DataTable';

type TestRow = {
  id: number;
  name: string;
};

const columns: DataTableColumn<TestRow>[] = [
  {
    key: 'name',
    label: 'Name',
    headerStyle: { minWidth: 120 },
    cellStyle: { whiteSpace: 'nowrap' },
  },
];

const data: TestRow[] = [{ id: 1, name: 'Alice' }];

const setDesktopMatchMedia = () => {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: query.includes('min-width'),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

const renderWithProvider = (ui: React.ReactElement) => {
  setDesktopMatchMedia();
  return render(<MantineProvider>{ui}</MantineProvider>);
};

describe('DataTable', () => {
  it('calls onRowClick when row is clicked', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();

    renderWithProvider(<DataTable columns={columns} data={data} onRowClick={onRowClick} />);

    const row = screen.getByText('Alice').closest('tr');
    if (!row) throw new Error('Row not found');

    await user.click(row);
    expect(onRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('calls onRowClick when row is activated via keyboard', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();

    renderWithProvider(<DataTable columns={columns} data={data} onRowClick={onRowClick} />);

    const row = screen.getByText('Alice').closest('tr');
    if (!row) throw new Error('Row not found');

    row.focus();
    await user.keyboard('{Enter}');

    expect(onRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('applies header and cell styles from column definition', () => {
    renderWithProvider(<DataTable columns={columns} data={data} />);

    const header = screen.getByRole('columnheader', { name: 'Name' });
    expect(header).toHaveStyle({ minWidth: '120px' });

    const cell = screen.getByText('Alice').closest('td');
    if (!cell) throw new Error('Cell not found');
    expect(cell).toHaveStyle({ whiteSpace: 'nowrap' });
  });
});
