-- Donation rooms: guest donations can be routed to a specific room
-- (an active entity tagged "room") instead of the general F0 entity.
-- For recurring Stripe donations the chosen recipient is stored on the
-- StripeAuthorization record, which requires a new column.
--
-- Schema is created by BaseModel.metadata.create_all() on startup, which
-- does NOT alter existing tables — run this once against any database that
-- already has the stripe_authorizations table (e.g. prod):
--
--   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
--       exec -T db psql -U postgres -d refinance < docs/donation_recipient.sql

-- 1) Donation recipient on stripe authorizations (idempotent)
ALTER TABLE stripe_authorizations
    ADD COLUMN IF NOT EXISTS donation_recipient_entity_id INTEGER REFERENCES entities(id);
