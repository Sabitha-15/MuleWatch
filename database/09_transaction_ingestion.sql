/*
=========================================================
MULEWATCH - TRANSACTION INGESTION SUPPORT
=========================================================
*/

ALTER TABLE transaction
ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100);

CREATE UNIQUE INDEX IF NOT EXISTS
idx_transaction_idempotency_key
ON transaction(idempotency_key)
WHERE idempotency_key IS NOT NULL;