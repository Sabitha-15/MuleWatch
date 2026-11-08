/* ============================================================
   MULEWATCH - PHASE 2 / CUSTOMER MANAGEMENT FOUNDATION
   PostgreSQL migration

   Adds:
   1. Customer profile audit log
   2. Audit trigger for customer updates
   3. Procedure to safely change customer status
   4. Function returning a customer's account/transaction summary

   Safe to re-run: uses IF NOT EXISTS / CREATE OR REPLACE.
   Existing customer/account/transaction records are not modified.
   ============================================================ */

-- 1. Audit table. Keep the audit record even if a customer is later
--    removed; customer_id becomes NULL rather than deleting the audit.
CREATE TABLE IF NOT EXISTS customer_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    action_type VARCHAR(20) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT,
    CONSTRAINT fk_customer_audit_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE SET NULL,
    CONSTRAINT chk_customer_audit_action
        CHECK (action_type IN ('UPDATE'))
);

CREATE INDEX IF NOT EXISTS idx_customer_audit_customer_time
    ON customer_audit_log(customer_id, changed_at DESC);

-- 2. Trigger function: record only meaningful customer changes.
CREATE OR REPLACE FUNCTION fn_audit_customer_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF ROW(OLD.full_name, OLD.email, OLD.phone, OLD.date_of_birth, OLD.status)
       IS DISTINCT FROM
       ROW(NEW.full_name, NEW.email, NEW.phone, NEW.date_of_birth, NEW.status)
    THEN
        INSERT INTO customer_audit_log (
            customer_id,
            action_type,
            old_data,
            new_data
        )
        VALUES (
            OLD.customer_id,
            'UPDATE',
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
    END IF;

    RETURN NEW;
END;
$$;

-- Recreate only this Phase 2 trigger, avoiding duplicate trigger execution.
DROP TRIGGER IF EXISTS trg_phase2_customer_audit ON customer;

CREATE TRIGGER trg_phase2_customer_audit
AFTER UPDATE ON customer
FOR EACH ROW
EXECUTE FUNCTION fn_audit_customer_update();

-- 3. Procedure: validate and update customer status.
--    The audit trigger automatically records the change.
CREATE OR REPLACE PROCEDURE sp_phase2_update_customer_status(
    IN p_customer_id BIGINT,
    IN p_new_status VARCHAR(20),
    IN p_change_reason TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status VARCHAR(20);
    v_normalized_status VARCHAR(20);
BEGIN
    v_normalized_status := UPPER(TRIM(p_new_status));

    IF v_normalized_status NOT IN ('ACTIVE', 'INACTIVE', 'BLOCKED') THEN
        RAISE EXCEPTION
            'Invalid customer status: %. Allowed values: ACTIVE, INACTIVE, BLOCKED.',
            p_new_status;
    END IF;

    SELECT status
      INTO v_current_status
      FROM customer
     WHERE customer_id = p_customer_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer ID % does not exist.', p_customer_id;
    END IF;

    IF v_current_status = v_normalized_status THEN
        RAISE NOTICE 'Customer % already has status %.',
            p_customer_id, v_normalized_status;
        RETURN;
    END IF;

    UPDATE customer
       SET status = v_normalized_status
     WHERE customer_id = p_customer_id;

    -- Attach the reason to the audit row created by the trigger.
    UPDATE customer_audit_log
       SET change_reason = p_change_reason
     WHERE audit_id = (
         SELECT MAX(audit_id)
           FROM customer_audit_log
          WHERE customer_id = p_customer_id
     );
END;
$$;

-- 4. Function: customer-level summary for the Customer Management UI
--    and investigation reports.
CREATE OR REPLACE FUNCTION fn_phase2_customer_summary(
    p_customer_id BIGINT
)
RETURNS TABLE (
    customer_id BIGINT,
    full_name VARCHAR(100),
    customer_status VARCHAR(20),
    account_count BIGINT,
    active_account_count BIGINT,
    total_account_balance NUMERIC,
    transaction_count BIGINT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM customer c WHERE c.customer_id = p_customer_id
    ) THEN
        RAISE EXCEPTION 'Customer ID % does not exist.', p_customer_id;
    END IF;

    RETURN QUERY
    SELECT
        c.customer_id,
        c.full_name,
        c.status,
        (SELECT COUNT(*)
           FROM account a
          WHERE a.customer_id = c.customer_id)::BIGINT,
        (SELECT COUNT(*)
           FROM account a
          WHERE a.customer_id = c.customer_id
            AND a.status = 'ACTIVE')::BIGINT,
        COALESCE((SELECT SUM(a.balance)
                    FROM account a
                   WHERE a.customer_id = c.customer_id), 0)::NUMERIC,
        (SELECT COUNT(DISTINCT t.transaction_id)
           FROM account a
           JOIN transaction t
             ON t.sender_account_id = a.account_id
             OR t.receiver_account_id = a.account_id
          WHERE a.customer_id = c.customer_id)::BIGINT
    FROM customer c
    WHERE c.customer_id = p_customer_id;
END;
$$;

-- 5. Verification queries (run after the migration).
-- SELECT routine_name, routine_type
-- FROM information_schema.routines
-- WHERE routine_name IN (
--   'fn_audit_customer_update',
--   'sp_phase2_update_customer_status',
--   'fn_phase2_customer_summary'
-- );
--
-- SELECT customer_id, full_name, status
-- FROM customer
-- ORDER BY customer_id;
--
-- SELECT * FROM fn_phase2_customer_summary(1);
--
-- CALL sp_phase2_update_customer_status(1, 'INACTIVE', 'Phase 2 audit test');
-- SELECT * FROM customer_audit_log ORDER BY audit_id DESC LIMIT 5;
