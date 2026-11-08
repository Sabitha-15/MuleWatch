/*
=========================================================
MULEWATCH - INVESTIGATION FINDINGS
=========================================================
*/

ALTER TABLE fraud_case
ADD COLUMN IF NOT EXISTS investigation_finding TEXT;

ALTER TABLE fraud_case
ADD COLUMN IF NOT EXISTS finding_type VARCHAR(30);

ALTER TABLE fraud_case
ADD COLUMN IF NOT EXISTS finding_recorded_at TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_fraud_case_finding_type'
    ) THEN
        ALTER TABLE fraud_case
        ADD CONSTRAINT chk_fraud_case_finding_type
        CHECK (
            finding_type IS NULL
            OR finding_type IN (
                'SUSPICIOUS',
                'LEGITIMATE',
                'INCONCLUSIVE'
            )
        );
    END IF;
END $$;