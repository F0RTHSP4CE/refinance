-- Repair historical transactions that settled multi-recipient invoice items.
--
-- For each transaction linked to an invoice item, this script:
--   1. sets transactions.invoice_id to the item's parent invoice;
--   2. copies every tag from that invoice to the transaction, without
--      removing transaction-specific tags such as "automatic".
--
-- The repair is idempotent: rerunning it makes no further changes.
-- Back up production first, then run with:
--
--   make db-backup ENV=prod
--   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
--       exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d refinance \
--       < docs/repair_multi_recipient_transactions.sql
--
-- To preview without keeping changes, replace COMMIT with ROLLBACK.
-- Deploy the application fix (or stop the old API/worker) before running this
-- so the old auto-pay code cannot create more incomplete rows concurrently.

\set ON_ERROR_STOP on

BEGIN;

-- Preview the work that will be performed.
SELECT COUNT(*) AS transactions_with_missing_or_wrong_invoice_id
FROM transactions AS transaction
JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
WHERE transaction.invoice_id IS DISTINCT FROM item.invoice_id;

SELECT COUNT(*) AS missing_transaction_tag_links
FROM (
    SELECT DISTINCT transaction.id AS transaction_id, invoice_tag.tag_id
    FROM transactions AS transaction
    JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
    JOIN invoices_tags AS invoice_tag ON invoice_tag.invoice_id = item.invoice_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM transactions_tags AS transaction_tag
        WHERE transaction_tag.transaction_id = transaction.id
          AND transaction_tag.tag_id = invoice_tag.tag_id
    )
) AS missing_links;

-- Restore the direct parent-invoice link. Deriving it through invoice_items
-- prevents an incorrect invoice_id from being preserved.
UPDATE transactions AS transaction
SET invoice_id = item.invoice_id
FROM invoice_items AS item
WHERE item.id = transaction.invoice_item_id
  AND transaction.invoice_id IS DISTINCT FROM item.invoice_id;

-- Add the parent invoice's tags. Existing transaction tags are preserved.
INSERT INTO transactions_tags (transaction_id, tag_id)
SELECT DISTINCT transaction.id, invoice_tag.tag_id
FROM transactions AS transaction
JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
JOIN invoices_tags AS invoice_tag ON invoice_tag.invoice_id = item.invoice_id
WHERE NOT EXISTS (
    SELECT 1
    FROM transactions_tags AS transaction_tag
    WHERE transaction_tag.transaction_id = transaction.id
      AND transaction_tag.tag_id = invoice_tag.tag_id
);

-- Both checks must return zero before the transaction is committed.
SELECT COUNT(*) AS remaining_wrong_invoice_ids
FROM transactions AS transaction
JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
WHERE transaction.invoice_id IS DISTINCT FROM item.invoice_id;

SELECT COUNT(*) AS remaining_missing_transaction_tag_links
FROM (
    SELECT DISTINCT transaction.id AS transaction_id, invoice_tag.tag_id
    FROM transactions AS transaction
    JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
    JOIN invoices_tags AS invoice_tag ON invoice_tag.invoice_id = item.invoice_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM transactions_tags AS transaction_tag
        WHERE transaction_tag.transaction_id = transaction.id
          AND transaction_tag.tag_id = invoice_tag.tag_id
    )
) AS missing_links;

-- Refuse to commit if either invariant is still broken.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM transactions AS transaction
        JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
        WHERE transaction.invoice_id IS DISTINCT FROM item.invoice_id
    ) THEN
        RAISE EXCEPTION 'multi-recipient transactions still have incorrect invoice_id values';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM transactions AS transaction
        JOIN invoice_items AS item ON item.id = transaction.invoice_item_id
        JOIN invoices_tags AS invoice_tag ON invoice_tag.invoice_id = item.invoice_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM transactions_tags AS transaction_tag
            WHERE transaction_tag.transaction_id = transaction.id
              AND transaction_tag.tag_id = invoice_tag.tag_id
        )
    ) THEN
        RAISE EXCEPTION 'multi-recipient transactions are still missing invoice tags';
    END IF;
END $$;

COMMIT;
