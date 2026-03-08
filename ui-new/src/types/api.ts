export type Tag = {
  id: number;
  name: string;
  comment?: string | null;
  created_at?: string;
  modified_at?: string | null;
};

export type BalanceSnapshot = {
  draft: Record<string, string>;
  completed: Record<string, string>;
};

export type ActorEntity = {
  id: number;
  name: string;
  active: boolean;
  comment: string;
};

export type EntityAuth = {
  telegram_id?: string | number | null;
  signal_id?: string | number | null;
};

export type Entity = ActorEntity & {
  tags: Tag[];
  auth?: EntityAuth | null;
  created_at: string;
  modified_at?: string | null;
};

export type EntityRef = {
  id: number;
  name: string;
  active: boolean;
  comment?: string | null;
  tags?: Tag[];
};

export type TreasuryRef = {
  id: number;
  name: string;
  active?: boolean;
  comment?: string | null;
  author_entity_id?: number | null;
  author_entity?: EntityRef | null;
  balances?: BalanceSnapshot | null;
  created_at?: string;
  modified_at?: string | null;
};

export type Transaction = {
  id: number;
  created_at: string;
  from_entity_id: number;
  from_entity: EntityRef;
  to_entity_id: number;
  to_entity: EntityRef;
  amount: string;
  currency: string;
  status: 'draft' | 'completed';
  tags: Tag[];
  comment?: string | null;
  invoice_id?: number | null;
  actor_entity_id: number;
  actor_entity: EntityRef;
  from_treasury_id?: number | null;
  to_treasury_id?: number | null;
  from_treasury?: TreasuryRef | null;
  to_treasury?: TreasuryRef | null;
};

export type InvoiceAmount = {
  currency: string;
  amount: string;
};

export type Invoice = {
  id: number;
  created_at: string;
  billing_period?: string | null;
  from_entity_id: number;
  from_entity: EntityRef;
  to_entity_id: number;
  to_entity: EntityRef;
  amounts: InvoiceAmount[];
  comment?: string | null;
  status: 'pending' | 'paid' | 'cancelled';
  tags: Tag[];
  actor_entity_id: number;
  actor_entity: EntityRef;
  transaction_id?: number | null;
};

export type SplitParticipant = {
  entity: Entity;
  fixed_amount?: string | null;
};

export type SplitSharePreview = {
  current_share: string;
  next_share: string;
  average_share: string;
};

export type Split = {
  id: number;
  created_at: string;
  modified_at?: string | null;
  comment?: string | null;
  actor_entity: Entity;
  recipient_entity: Entity;
  participants: SplitParticipant[];
  amount: string;
  currency: string;
  collected_amount: string;
  performed: boolean;
  share_preview: SplitSharePreview;
  performed_transactions: Transaction[];
  tags: Tag[];
};

export type MonthlyFee = {
  year: number;
  month: number;
  amounts: Record<string, string>;
  total_usd: number;
  unpaid_invoice_id?: number | null;
  paid_invoice_id?: number | null;
  unpaid_invoice_amounts?: Record<string, string> | null;
};

export type FeeRow = {
  entity: Entity;
  fees: MonthlyFee[];
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  skip: number;
  limit: number;
};
