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
  tags: { id: number; name: string }[];
  auth?: EntityAuth | null;
  created_at: string;
  modified_at?: string | null;
};

export type EntityRef = {
  id: number;
  name: string;
  active: boolean;
  comment?: string | null;
  tags?: { id: number; name: string }[];
};

export type TreasuryRef = {
  id: number;
  name: string;
  comment?: string | null;
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
  tags: { id: number; name: string }[];
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
  status: string;
  tags: { id: number; name: string }[];
  actor_entity_id: number;
  actor_entity: EntityRef;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  skip: number;
  limit: number;
};
