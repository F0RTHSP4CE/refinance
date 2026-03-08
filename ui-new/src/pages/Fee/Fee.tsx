import {
  Alert,
  Anchor,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, type CSSProperties } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getEntities } from '@/api/entities';
import { getFees } from '@/api/fees';
import { deleteInvoice, getInvoice, getInvoices } from '@/api/invoices';
import { InvoiceDetailsModal } from '@/components/Invoices/InvoiceDetailsModal';
import { InvoiceEditorModal } from '@/components/Invoices/InvoiceEditorModal';
import { InvoicePayModal } from '@/components/Invoices/InvoicePayModal';
import {
  AccentSurface,
  AmountsCurrency,
  AppCard,
  DataTable,
  RelativeDate,
  StatusBadge,
  TagList,
  type DataTableColumn,
} from '@/components/ui';
import type { FeeRow, Invoice, MonthlyFee } from '@/types/api';

const MAX_ITEMS = 500;

type FeeTab = 'invoices' | 'fees';

type FeeCellState = {
  row: FeeRow;
  fee: MonthlyFee;
};

type FeeVisualState = 'paid' | 'pending' | 'empty';

const padMonth = (value: number) => String(value).padStart(2, '0');

const MATRIX_RESIDENT_WIDTH = 240;
const MATRIX_MONTH_MIN_WIDTH = 160;
const MATRIX_BORDER = 'rgba(255, 255, 255, 0.08)';
const MATRIX_HEADER_SURFACE = 'var(--mantine-color-body)';
const MATRIX_STICKY_SURFACE = 'var(--mantine-color-body)';
const MATRIX_EMPTY_SURFACE = 'transparent';

const STATUS_LEGEND: Array<{
  label: string;
  background: string;
  border: string;
  dot: string;
}> = [
  {
    label: 'Paid',
    background: 'rgba(21, 128, 61, 0.18)',
    border: 'rgba(74, 222, 128, 0.28)',
    dot: 'rgba(74, 222, 128, 0.9)',
  },
  {
    label: 'Pending',
    background: 'rgba(146, 64, 14, 0.2)',
    border: 'rgba(251, 191, 36, 0.28)',
    dot: 'rgba(251, 191, 36, 0.92)',
  },
  {
    label: 'No invoice',
    background: 'rgba(30, 41, 59, 0.76)',
    border: 'rgba(148, 163, 184, 0.22)',
    dot: 'rgba(148, 163, 184, 0.9)',
  },
];

const createStickyCellStyle = ({
  left,
  width,
  isHeader = false,
  withShadow = false,
}: {
  left: number;
  width: number;
  isHeader?: boolean;
  withShadow?: boolean;
}): CSSProperties => ({
  position: 'sticky',
  left,
  zIndex: isHeader ? 3 : 2,
  minWidth: width,
  width,
  maxWidth: width,
  background: isHeader ? MATRIX_HEADER_SURFACE : MATRIX_STICKY_SURFACE,
  boxShadow: `inset -1px 0 0 ${MATRIX_BORDER}`,
  borderRight: withShadow ? `1px solid ${MATRIX_BORDER}` : undefined,
});

const MATRIX_TABLE_STYLE: CSSProperties = {
  minWidth: '100%',
  width: 'max-content',
  borderCollapse: 'separate',
  borderSpacing: 0,
  tableLayout: 'auto',
};

const MATRIX_HEAD_CELL_STYLE: CSSProperties = {
  background: MATRIX_HEADER_SURFACE,
  borderBottom: `1px solid ${MATRIX_BORDER}`,
  color: 'var(--mantine-color-gray-3)',
  fontSize: '0.78rem',
  fontWeight: 700,
  letterSpacing: '0.08em',
  padding: '0.8rem 0.9rem',
  textTransform: 'uppercase',
  whiteSpace: 'nowrap',
};

const MATRIX_MONTH_CELL_STYLE: CSSProperties = {
  minWidth: MATRIX_MONTH_MIN_WIDTH,
  width: MATRIX_MONTH_MIN_WIDTH,
  padding: '0.65rem 0.7rem',
  borderBottom: `1px solid ${MATRIX_BORDER}`,
  background: 'transparent',
  verticalAlign: 'top',
};

const MATRIX_EMPTY_CELL_STYLE: CSSProperties = {
  ...MATRIX_MONTH_CELL_STYLE,
  background: MATRIX_EMPTY_SURFACE,
};

const toMonthInput = (value: Date) => `${value.getFullYear()}-${padMonth(value.getMonth() + 1)}`;

const subtractMonths = (value: Date, monthsBack: number) => {
  const next = new Date(value);
  const day = next.getDate();
  next.setDate(1);
  next.setMonth(next.getMonth() - monthsBack);
  const maxDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
  next.setDate(Math.min(day, maxDay));
  return next;
};

const formatBillingPeriod = (period?: string | null) => {
  if (!period) return '—';
  const date = new Date(period);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatFeeMonth = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleDateString('en-US', {
    month: 'short',
    year: 'numeric',
  });

const formatAccessibleFeeMonth = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

const formatAmountLines = (amounts: Record<string, string> | null | undefined) => {
  if (!amounts || Object.keys(amounts).length === 0) return [];
  return Object.entries(amounts).map(([currency, amount]) => `${amount} ${currency.toUpperCase()}`);
};

const formatAmountEntries = (amounts: Record<string, string> | null | undefined) => {
  const lines = formatAmountLines(amounts);
  return lines.length > 0 ? lines.join(' · ') : '—';
};

const getInvoiceTone = (status: Invoice['status']) => (status === 'paid' ? 'positive' : 'neutral');
const getFeeTone = (fee: MonthlyFee) => (fee.paid_invoice_id ? 'positive' : 'neutral');

const getFeeVisualState = (fee: MonthlyFee): FeeVisualState => {
  if (fee.paid_invoice_id) return 'paid';
  if (fee.unpaid_invoice_id) return 'pending';
  return 'empty';
};

const getFeeStatusLabel = (fee: MonthlyFee) => {
  const state = getFeeVisualState(fee);
  return state === 'empty' ? 'no invoice' : state;
};

const getFeeCellSurface = (fee: MonthlyFee) => {
  const state = getFeeVisualState(fee);

  if (state === 'paid') {
    return {
      state,
      background: 'rgba(21, 128, 61, 0.18)',
      border: 'rgba(74, 222, 128, 0.3)',
      color: 'var(--mantine-color-gray-0)',
    };
  }

  if (state === 'pending') {
    return {
      state,
      background: 'rgba(146, 64, 14, 0.2)',
      border: 'rgba(251, 191, 36, 0.3)',
      color: 'var(--mantine-color-gray-0)',
    };
  }

  return {
    state,
    background: 'rgba(255, 255, 255, 0.02)',
    border: 'rgba(148, 163, 184, 0.18)',
    color: 'var(--mantine-color-gray-0)',
  };
};

const FeeCellModal = ({
  cell,
  opened,
  onClose,
  onOpenInvoice,
}: {
  cell: FeeCellState | null;
  opened: boolean;
  onClose: () => void;
  onOpenInvoice: (invoiceId: number) => void;
}) => {
  const invoiceId = cell?.fee.unpaid_invoice_id ?? cell?.fee.paid_invoice_id ?? null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        cell
          ? `${cell.row.entity.name} · ${formatFeeMonth(cell.fee.year, cell.fee.month)}`
          : 'Fee details'
      }
      centered
    >
      {cell ? (
        <Stack gap="md">
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Status
            </Text>
            <StatusBadge tone={getFeeTone(cell.fee)}>
              {cell.fee.paid_invoice_id
                ? 'paid'
                : cell.fee.unpaid_invoice_id
                  ? 'pending'
                  : 'no invoice'}
            </StatusBadge>
          </Group>

          <Stack gap={4}>
            <Text size="sm" c="dimmed">
              Amounts
            </Text>
            <Text>{formatAmountEntries(cell.fee.amounts)}</Text>
          </Stack>

          <Stack gap={4}>
            <Text size="sm" c="dimmed">
              Pending invoice amounts
            </Text>
            <Text>{formatAmountEntries(cell.fee.unpaid_invoice_amounts)}</Text>
          </Stack>

          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Related invoices
            </Text>
            <Text size="sm">
              {cell.fee.unpaid_invoice_id ?? '—'} / {cell.fee.paid_invoice_id ?? '—'}
            </Text>
          </Group>

          {invoiceId ? (
            <Button variant="default" onClick={() => onOpenInvoice(invoiceId)}>
              Open invoice
            </Button>
          ) : null}
        </Stack>
      ) : null}
    </Modal>
  );
};

export const Fee = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const now = useMemo(() => new Date(), []);
  const defaultToPeriod = useMemo(() => toMonthInput(now), [now]);
  const defaultFromPeriod = useMemo(() => toMonthInput(subtractMonths(now, 5)), [now]);
  const initialFeeRange = useMemo(
    () => ({
      from: defaultFromPeriod,
      to: defaultToPeriod,
    }),
    [defaultFromPeriod, defaultToPeriod]
  );

  const [entityFilter, setEntityFilter] = useState<string | null>(null);
  const [fromEntityFilter, setFromEntityFilter] = useState<string | null>(null);
  const [toEntityFilter, setToEntityFilter] = useState<string | null>(null);
  const [actorEntityFilter, setActorEntityFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [billingPeriodFilter, setBillingPeriodFilter] = useState('');
  const [fromPeriod, setFromPeriod] = useState(defaultFromPeriod);
  const [toPeriod, setToPeriod] = useState(defaultToPeriod);
  const [invoiceEditorOpened, setInvoiceEditorOpened] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
  const [payInvoiceState, setPayInvoiceState] = useState<Invoice | null>(null);
  const [feeCellState, setFeeCellState] = useState<FeeCellState | null>(null);
  const [selectedInvoicePreview, setSelectedInvoicePreview] = useState<Invoice | null>(null);

  const effectiveFromPeriod = fromPeriod || defaultFromPeriod;
  const effectiveToPeriod = toPeriod || defaultToPeriod;
  const isRangeDirty = fromPeriod !== initialFeeRange.from || toPeriod !== initialFeeRange.to;
  const normalizedFromPeriod =
    effectiveFromPeriod <= effectiveToPeriod ? effectiveFromPeriod : effectiveToPeriod;
  const normalizedToPeriod =
    effectiveFromPeriod <= effectiveToPeriod ? effectiveToPeriod : effectiveFromPeriod;

  const activeTab = (searchParams.get('tab') as FeeTab) === 'fees' ? 'fees' : 'invoices';
  const selectedInvoiceId = Number(searchParams.get('invoiceId') || '') || null;

  const entitiesQuery = useQuery({
    queryKey: ['entities', 'fee-page'],
    queryFn: ({ signal }) => getEntities({ limit: MAX_ITEMS, signal }),
  });

  const invoicesQuery = useQuery({
    queryKey: [
      'invoices',
      'fee-page',
      entityFilter,
      fromEntityFilter,
      toEntityFilter,
      actorEntityFilter,
      statusFilter,
      billingPeriodFilter,
    ],
    queryFn: ({ signal }) =>
      getInvoices({
        entity_id: entityFilter ? Number(entityFilter) : undefined,
        from_entity_id: fromEntityFilter ? Number(fromEntityFilter) : undefined,
        to_entity_id: toEntityFilter ? Number(toEntityFilter) : undefined,
        actor_entity_id: actorEntityFilter ? Number(actorEntityFilter) : undefined,
        status: (statusFilter as Invoice['status']) ?? undefined,
        billing_period: billingPeriodFilter.trim() ? `${billingPeriodFilter.trim()}-01` : undefined,
        limit: MAX_ITEMS,
        signal,
      }),
  });

  const selectedInvoiceQuery = useQuery({
    queryKey: ['invoice', selectedInvoiceId],
    queryFn: ({ signal }) => getInvoice(selectedInvoiceId!, signal),
    enabled: selectedInvoiceId != null,
  });

  const feesQuery = useQuery({
    queryKey: ['fees', normalizedFromPeriod, normalizedToPeriod],
    queryFn: ({ signal }) =>
      getFees({
        from_period: `${normalizedFromPeriod}-01`,
        to_period: `${normalizedToPeriod}-01`,
        signal,
      }),
  });

  const deleteInvoiceMutation = useMutation({
    mutationFn: async (invoiceId: number) => deleteInvoice(invoiceId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
        queryClient.invalidateQueries({ queryKey: ['invoice'] }),
        queryClient.invalidateQueries({ queryKey: ['pendingInvoices'] }),
        queryClient.invalidateQueries({ queryKey: ['fees'] }),
      ]);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('invoiceId');
      setSearchParams(nextParams);
    },
  });

  const entityOptions =
    entitiesQuery.data?.items
      .map((entity) => ({
        value: String(entity.id),
        label: entity.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label)) ?? [];

  const prefetchInvoice = (invoiceId: number) => {
    return queryClient.prefetchQuery({
      queryKey: ['invoice', invoiceId],
      queryFn: ({ signal }) => getInvoice(invoiceId, signal),
    });
  };

  const openInvoice = (invoiceOrPreview: number | Invoice, nextTab?: FeeTab) => {
    const invoiceId = typeof invoiceOrPreview === 'number' ? invoiceOrPreview : invoiceOrPreview.id;
    const preview = typeof invoiceOrPreview === 'number' ? null : invoiceOrPreview;

    setSelectedInvoicePreview(preview);
    if (preview) {
      queryClient.setQueryData(['invoice', invoiceId], preview);
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('invoiceId', String(invoiceId));
    if (nextTab) {
      nextParams.set('tab', nextTab);
    }
    setSearchParams(nextParams);
  };

  const closeInvoiceModal = () => {
    setSelectedInvoicePreview(null);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('invoiceId');
    setSearchParams(nextParams);
  };

  const selectedInvoice =
    selectedInvoiceQuery.data ??
    selectedInvoicePreview ??
    invoicesQuery.data?.items.find((invoice) => invoice.id === selectedInvoiceId) ??
    null;
  const selectedInvoiceLoading =
    selectedInvoiceId != null && selectedInvoice == null && selectedInvoiceQuery.isFetching;

  const invoiceColumns: DataTableColumn<Invoice>[] = [
    { key: 'id', label: 'ID', render: (invoice) => <Text size="sm">{invoice.id}</Text> },
    {
      key: 'created_at',
      label: 'Created',
      render: (invoice) => <RelativeDate isoString={invoice.created_at} />,
    },
    {
      key: 'billing_period',
      label: 'Billing period',
      render: (invoice) => <Text size="sm">{formatBillingPeriod(invoice.billing_period)}</Text>,
    },
    {
      key: 'from_entity',
      label: 'From',
      render: (invoice) => <Text size="sm">{invoice.from_entity.name}</Text>,
    },
    {
      key: 'to_entity',
      label: 'To',
      render: (invoice) => <Text size="sm">{invoice.to_entity.name}</Text>,
    },
    {
      key: 'amounts',
      label: 'Amounts',
      render: (invoice) => <AmountsCurrency amounts={invoice.amounts} />,
    },
    {
      key: 'status',
      label: 'Status',
      render: (invoice) => (
        <StatusBadge tone={getInvoiceTone(invoice.status)}>{invoice.status}</StatusBadge>
      ),
    },
    {
      key: 'tags',
      label: 'Tags',
      render: (invoice) =>
        invoice.tags.length ? (
          <TagList tags={invoice.tags} mode="compact" />
        ) : (
          <Text size="sm">—</Text>
        ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (invoice) => (
        <Button
          variant="subtle"
          size="xs"
          onClick={() => openInvoice(invoice, 'invoices')}
          onMouseEnter={() => void prefetchInvoice(invoice.id)}
          onFocus={() => void prefetchInvoice(invoice.id)}
        >
          Open
        </Button>
      ),
    },
  ];

  const feeRows = useMemo(
    () => (feesQuery.data ?? []).filter((row) => row.fees.length > 0),
    [feesQuery.data]
  );

  const feeMonths = useMemo(() => {
    const monthMap = new Map<string, MonthlyFee>();
    for (const row of feeRows) {
      for (const fee of row.fees) {
        monthMap.set(`${fee.year}-${fee.month}`, fee);
      }
    }
    return Array.from(monthMap.values()).sort((left, right) =>
      left.year === right.year ? left.month - right.month : left.year - right.year
    );
  }, [feeRows]);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Fee</Title>
          <Text c="dimmed" size="sm">
            Manage invoices and inspect fee history from one place. Details stay in modals instead
            of separate screens.
          </Text>
        </div>
        <Button
          variant="default"
          onClick={() => {
            setEditingInvoice(null);
            setInvoiceEditorOpened(true);
          }}
        >
          Create invoice
        </Button>
      </Group>

      <Tabs
        value={activeTab}
        onChange={(value) => {
          const nextParams = new URLSearchParams(searchParams);
          nextParams.set('tab', value === 'fees' ? 'fees' : 'invoices');
          setSearchParams(nextParams);
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="invoices">
            <Text component="span" className="text-xl">
              Invoices
            </Text>
          </Tabs.Tab>
          <Tabs.Tab value="fees">
            <Text component="span" className="text-xl">
              Fees
            </Text>
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="invoices" pt="md">
          <Stack gap="lg">
            <AccentSurface>
              <Stack gap="md">
                <Text fw={600}>Invoice filters</Text>

                <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <Select
                    label="Entity"
                    placeholder="Any entity"
                    searchable
                    clearable
                    data={entityOptions}
                    value={entityFilter}
                    onChange={setEntityFilter}
                  />
                  <Select
                    label="From"
                    placeholder="Any payer"
                    searchable
                    clearable
                    data={entityOptions}
                    value={fromEntityFilter}
                    onChange={setFromEntityFilter}
                  />
                  <Select
                    label="To"
                    placeholder="Any receiver"
                    searchable
                    clearable
                    data={entityOptions}
                    value={toEntityFilter}
                    onChange={setToEntityFilter}
                  />
                  <Select
                    label="Actor"
                    placeholder="Any actor"
                    searchable
                    clearable
                    data={entityOptions}
                    value={actorEntityFilter}
                    onChange={setActorEntityFilter}
                  />
                  <Select
                    label="Status"
                    placeholder="Any status"
                    clearable
                    data={[
                      { value: 'pending', label: 'Pending' },
                      { value: 'paid', label: 'Paid' },
                      { value: 'cancelled', label: 'Cancelled' },
                    ]}
                    value={statusFilter}
                    onChange={setStatusFilter}
                  />
                  <TextInput
                    type="month"
                    label="Billing period"
                    value={billingPeriodFilter}
                    onChange={(event) => setBillingPeriodFilter(event.currentTarget.value)}
                  />
                </div>
              </Stack>
            </AccentSurface>

            <AppCard>
              <DataTable
                columns={invoiceColumns}
                data={invoicesQuery.data?.items ?? []}
                emptyMessage={
                  invoicesQuery.isLoading ? 'Loading invoices...' : 'No invoices found.'
                }
                onRowClick={(invoice) => openInvoice(invoice, 'invoices')}
                getRowAriaLabel={(invoice) => `Open invoice #${invoice.id}`}
              />
            </AppCard>

            {deleteInvoiceMutation.isError ? (
              <Alert color="red" title="Could not delete invoice">
                {deleteInvoiceMutation.error.message}
              </Alert>
            ) : null}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="fees" pt="md">
          <Stack gap="lg">
            <AccentSurface>
              <Stack gap="md">
                <Group justify="space-between" align="center">
                  <Text fw={600}>Resident fee matrix</Text>
                  {isRangeDirty ? (
                    <Button
                      variant="subtle"
                      color="gray"
                      onClick={() => {
                        setFromPeriod(initialFeeRange.from);
                        setToPeriod(initialFeeRange.to);
                      }}
                    >
                      Reset range
                    </Button>
                  ) : null}
                </Group>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <TextInput
                    type="month"
                    label="From period"
                    value={fromPeriod}
                    onChange={(event) => setFromPeriod(event.currentTarget.value)}
                  />
                  <TextInput
                    type="month"
                    label="To period"
                    value={toPeriod}
                    onChange={(event) => setToPeriod(event.currentTarget.value)}
                  />
                </div>

                <Text size="sm" c="dimmed">
                  Only months with meaningful fee data are shown. Empty placeholder cells are
                  intentionally suppressed.
                </Text>
              </Stack>
            </AccentSurface>

            <AppCard>
              <Stack gap="md">
                <Group justify="space-between" align="flex-end" gap="md" wrap="wrap">
                  <div>
                    <Text fw={600}>Resident fee matrix</Text>
                    <Text size="sm" c="dimmed">
                      Scroll sideways to compare monthly fees when the matrix exceeds the card
                      width.
                    </Text>
                  </div>

                  <Group gap="xs" wrap="wrap">
                    {STATUS_LEGEND.map((item) => (
                      <Group
                        key={item.label}
                        gap={8}
                        wrap="nowrap"
                        style={{
                          background: item.background,
                          border: `1px solid ${item.border}`,
                          borderRadius: 999,
                          padding: '6px 10px',
                        }}
                      >
                        <span
                          aria-hidden="true"
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '999px',
                            background: item.dot,
                            display: 'inline-block',
                          }}
                        />
                        <Text size="xs" fw={700} c="gray.0" tt="uppercase">
                          {item.label}
                        </Text>
                      </Group>
                    ))}
                  </Group>
                </Group>

                {feesQuery.isLoading ? (
                  <Text c="dimmed">Loading fee history...</Text>
                ) : feeRows.length === 0 || feeMonths.length === 0 ? (
                  <Text c="dimmed">No fee history in the selected range.</Text>
                ) : (
                  <div
                    role="region"
                    aria-label="Resident fee matrix"
                    style={{
                      overflowX: 'auto',
                      overflowY: 'visible',
                      paddingBottom: 6,
                    }}
                  >
                    <Table style={MATRIX_TABLE_STYLE}>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th
                            style={{
                              ...MATRIX_HEAD_CELL_STYLE,
                              ...createStickyCellStyle({
                                left: 0,
                                width: MATRIX_RESIDENT_WIDTH,
                                isHeader: true,
                              }),
                            }}
                          >
                            Resident
                          </Table.Th>
                          {feeMonths.map((fee) => (
                            <Table.Th
                              key={`${fee.year}-${fee.month}`}
                              style={{
                                ...MATRIX_HEAD_CELL_STYLE,
                                minWidth: MATRIX_MONTH_MIN_WIDTH,
                                width: MATRIX_MONTH_MIN_WIDTH,
                              }}
                            >
                              {formatFeeMonth(fee.year, fee.month)}
                            </Table.Th>
                          ))}
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {feeRows.map((row) => {
                          const feeByMonth = new Map(
                            row.fees.map((fee) => [`${fee.year}-${fee.month}`, fee])
                          );

                          return (
                            <Table.Tr key={row.entity.id}>
                              <Table.Td
                                style={{
                                  ...createStickyCellStyle({
                                    left: 0,
                                    width: MATRIX_RESIDENT_WIDTH,
                                  }),
                                  borderBottom: `1px solid ${MATRIX_BORDER}`,
                                  padding: '0.9rem',
                                  verticalAlign: 'middle',
                                }}
                              >
                                <Stack gap={6} style={{ minWidth: 0 }}>
                                  <Anchor
                                    component={Link}
                                    fw={600}
                                    to={`/profile/${row.entity.id}`}
                                    underline="hover"
                                    style={{
                                      color: 'inherit',
                                      lineHeight: 1.2,
                                      width: 'fit-content',
                                    }}
                                  >
                                    {row.entity.name}
                                  </Anchor>
                                  {row.entity.tags.length ? (
                                    <TagList tags={row.entity.tags} mode="compact" />
                                  ) : null}
                                </Stack>
                              </Table.Td>
                              {feeMonths.map((monthCell) => {
                                const fee = feeByMonth.get(`${monthCell.year}-${monthCell.month}`);

                                if (!fee) {
                                  return (
                                    <Table.Td
                                      key={`${row.entity.id}-${monthCell.year}-${monthCell.month}`}
                                      style={MATRIX_EMPTY_CELL_STYLE}
                                    />
                                  );
                                }

                                const amountLines = formatAmountLines(
                                  fee.unpaid_invoice_amounts ?? fee.amounts
                                );
                                const surface = getFeeCellSurface(fee);
                                const statusLabel = getFeeStatusLabel(fee);

                                return (
                                  <Table.Td
                                    key={`${row.entity.id}-${fee.year}-${fee.month}`}
                                    style={MATRIX_MONTH_CELL_STYLE}
                                  >
                                    <UnstyledButton
                                      aria-label={`Open fee details for ${row.entity.name}, ${formatAccessibleFeeMonth(fee.year, fee.month)}, ${statusLabel}`}
                                      data-fee-state={surface.state}
                                      onClick={() => setFeeCellState({ row, fee })}
                                      onMouseEnter={() =>
                                        fee.paid_invoice_id || fee.unpaid_invoice_id
                                          ? void prefetchInvoice(
                                              fee.unpaid_invoice_id ?? fee.paid_invoice_id!
                                            )
                                          : undefined
                                      }
                                      onFocus={() =>
                                        fee.paid_invoice_id || fee.unpaid_invoice_id
                                          ? void prefetchInvoice(
                                              fee.unpaid_invoice_id ?? fee.paid_invoice_id!
                                            )
                                          : undefined
                                      }
                                      className="block w-full transition duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                                      style={{
                                        width: '100%',
                                        minHeight: 92,
                                        padding: '12px',
                                        borderRadius: 12,
                                        background: surface.background,
                                        border: `1px solid ${surface.border}`,
                                        color: surface.color,
                                        textAlign: 'left',
                                        outlineColor: surface.border,
                                      }}
                                    >
                                      <Stack gap={8}>
                                        <StatusBadge tone={getFeeTone(fee)} size="sm">
                                          {statusLabel}
                                        </StatusBadge>
                                        <Stack gap={3}>
                                          {amountLines.length > 0 ? (
                                            amountLines.map((line) => (
                                              <Text
                                                key={line}
                                                size="sm"
                                                fw={600}
                                                style={{
                                                  color: surface.color,
                                                  lineHeight: 1.35,
                                                  whiteSpace: 'nowrap',
                                                }}
                                              >
                                                {line}
                                              </Text>
                                            ))
                                          ) : (
                                            <Text
                                              size="sm"
                                              fw={600}
                                              c="dimmed"
                                              style={{ lineHeight: 1.35 }}
                                            >
                                              —
                                            </Text>
                                          )}
                                        </Stack>
                                      </Stack>
                                    </UnstyledButton>
                                  </Table.Td>
                                );
                              })}
                            </Table.Tr>
                          );
                        })}
                      </Table.Tbody>
                    </Table>
                  </div>
                )}
              </Stack>
            </AppCard>
          </Stack>
        </Tabs.Panel>
      </Tabs>

      <InvoiceDetailsModal
        opened={selectedInvoiceId != null}
        invoice={selectedInvoice}
        loading={selectedInvoiceLoading}
        onClose={closeInvoiceModal}
        onEdit={(invoice) => {
          setEditingInvoice(invoice);
          setInvoiceEditorOpened(true);
        }}
        onPay={(invoice) => setPayInvoiceState(invoice)}
        onDelete={(invoice) => deleteInvoiceMutation.mutate(invoice.id)}
      />

      <InvoiceEditorModal
        opened={invoiceEditorOpened}
        invoice={editingInvoice}
        onClose={() => {
          setInvoiceEditorOpened(false);
          setEditingInvoice(null);
        }}
        onSaved={(invoice) => {
          openInvoice(invoice);
        }}
      />

      <InvoicePayModal
        opened={payInvoiceState != null}
        invoice={payInvoiceState}
        onClose={() => setPayInvoiceState(null)}
      />

      <FeeCellModal
        opened={feeCellState != null}
        cell={feeCellState}
        onClose={() => setFeeCellState(null)}
        onOpenInvoice={(invoiceId) => {
          setFeeCellState(null);
          openInvoice(invoiceId);
        }}
      />
    </Stack>
  );
};
