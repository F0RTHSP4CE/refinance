import {
  ResponsiveDataView,
  type ResponsiveDataColumn,
  type ResponsiveDataViewProps,
} from '../ResponsiveDataView';

export type DataTableColumn<T> = ResponsiveDataColumn<T>;

type DataTableProps<T> = ResponsiveDataViewProps<T>;

export function DataTable<T extends Record<string, unknown>>({
  ...props
}: DataTableProps<T>) {
  return <ResponsiveDataView {...props} />;
}
