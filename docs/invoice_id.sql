-- 1) Invoice status enum (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoice_status') THEN
        CREATE TYPE invoice_status AS ENUM ('pending', 'paid', 'cancelled');
    END IF;
END $$;

-- 2) Invoices table (idempotent)
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    comment TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_at TIMESTAMP WITHOUT TIME ZONE,
    actor_entity_id INTEGER NOT NULL REFERENCES entities(id),
    from_entity_id INTEGER NOT NULL REFERENCES entities(id),
    to_entity_id INTEGER NOT NULL REFERENCES entities(id),
    amounts JSON NOT NULL,
    status invoice_status NOT NULL DEFAULT 'pending'
);

-- 3) Invoices tags join table
CREATE TABLE IF NOT EXISTS invoices_tags (
    invoice_id INTEGER REFERENCES invoices(id),
    tag_id INTEGER REFERENCES tags(id)
);

-- 4) Add invoice_id to transactions if missing
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS invoice_id INTEGER;

-- 5) Add FK + unique constraint if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'transactions_invoice_id_fkey'
          AND table_name = 'transactions'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT transactions_invoice_id_fkey
            FOREIGN KEY (invoice_id) REFERENCES invoices(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'transactions_invoice_id_key'
    ) THEN
        CREATE UNIQUE INDEX transactions_invoice_id_key ON transactions(invoice_id);
    END IF;
END $$;