/* ============================================================
   MULEWATCH - PHASE 2 ADVANCED DATABASE FEATURES
   PostgreSQL migration; safe to re-run.

   Feature 2: Advanced Transaction Explorer + status audit
   Feature 3: Recursive Account Network function
   Feature 4: Immutable Investigation Report snapshots
   ============================================================ */

-- ------------------------------------------------------------
-- FEATURE 2A: TRANSACTION EXPLORER VIEW + SEARCH INDEXES
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transaction_status_time
    ON transaction(status, txn_time DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_type_time
    ON transaction(transaction_type, txn_time DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_amount
    ON transaction(amount);
CREATE INDEX IF NOT EXISTS idx_transaction_receiver_time
    ON transaction(receiver_account_id, txn_time DESC);

CREATE OR REPLACE VIEW vw_phase2_transaction_explorer AS
SELECT
    t.transaction_id,
    t.txn_time,
    t.amount,
    t.transaction_type,
    t.channel,
    t.status,
    t.description,
    t.sender_account_id,
    sender.account_number AS sender_account_number,
    sender_customer.full_name AS sender_customer_name,
    t.receiver_account_id,
    receiver.account_number AS receiver_account_number,
    receiver_customer.full_name AS receiver_customer_name,
    t.beneficiary_id,
    b.beneficiary_name,
    latest_risk.risk_assessment_id,
    latest_risk.risk_score,
    latest_risk.risk_level,
    latest_risk.assessed_at,
    COALESCE(latest_risk.alert_count, 0)::BIGINT AS alert_count
FROM transaction t
JOIN account sender ON sender.account_id = t.sender_account_id
JOIN customer sender_customer ON sender_customer.customer_id = sender.customer_id
JOIN account receiver ON receiver.account_id = t.receiver_account_id
JOIN customer receiver_customer ON receiver_customer.customer_id = receiver.customer_id
LEFT JOIN beneficiary b ON b.beneficiary_id = t.beneficiary_id
LEFT JOIN LATERAL (
    SELECT
        ra.risk_assessment_id,
        ra.risk_score,
        ra.risk_level,
        ra.assessed_at,
        (SELECT COUNT(*) FROM fraud_alert fa
         WHERE fa.risk_assessment_id = ra.risk_assessment_id) AS alert_count
    FROM risk_assessment ra
    WHERE ra.transaction_id = t.transaction_id
    ORDER BY ra.assessed_at DESC, ra.risk_assessment_id DESC
    LIMIT 1
) latest_risk ON TRUE;

-- ------------------------------------------------------------
-- FEATURE 2B: TRANSACTION STATUS AUDIT
-- Only PENDING transactions may be finalized by the procedure.
-- Every status change is captured by the trigger.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction_status_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT,
    old_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT,
    CONSTRAINT fk_transaction_status_audit_transaction
        FOREIGN KEY (transaction_id) REFERENCES transaction(transaction_id)
        ON DELETE SET NULL,
    CONSTRAINT chk_transaction_audit_old_status
        CHECK (old_status IN ('SUCCESS', 'FAILED', 'PENDING')),
    CONSTRAINT chk_transaction_audit_new_status
        CHECK (new_status IN ('SUCCESS', 'FAILED', 'PENDING'))
);

CREATE INDEX IF NOT EXISTS idx_transaction_status_audit_txn_time
    ON transaction_status_audit(transaction_id, changed_at DESC);

CREATE OR REPLACE FUNCTION fn_phase2_audit_transaction_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_reason TEXT;
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        v_reason := NULLIF(current_setting('mulewatch.phase2_change_reason', TRUE), '');
        INSERT INTO transaction_status_audit (
            transaction_id, old_status, new_status, change_reason
        ) VALUES (
            OLD.transaction_id, OLD.status, NEW.status, v_reason
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_phase2_transaction_status_audit ON transaction;
CREATE TRIGGER trg_phase2_transaction_status_audit
AFTER UPDATE OF status ON transaction
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION fn_phase2_audit_transaction_status();

CREATE OR REPLACE PROCEDURE sp_phase2_update_transaction_status(
    IN p_transaction_id BIGINT,
    IN p_new_status VARCHAR(20),
    IN p_change_reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status VARCHAR(20);
    v_target_status VARCHAR(20);
BEGIN
    v_target_status := UPPER(TRIM(p_new_status));
    IF v_target_status IS NULL OR v_target_status NOT IN ('SUCCESS', 'FAILED') THEN
        RAISE EXCEPTION 'Invalid final transaction status: %. Use SUCCESS or FAILED.', p_new_status;
    END IF;
    IF p_change_reason IS NULL OR LENGTH(TRIM(p_change_reason)) = 0 THEN
        RAISE EXCEPTION 'A reason is required to finalize a transaction.';
    END IF;

    SELECT status INTO v_current_status
    FROM transaction
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction ID % does not exist.', p_transaction_id;
    END IF;
    IF v_current_status <> 'PENDING' THEN
        RAISE EXCEPTION 'Only PENDING transactions can be finalized. Current status: %.', v_current_status;
    END IF;

    PERFORM set_config('mulewatch.phase2_change_reason', TRIM(p_change_reason), TRUE);
    UPDATE transaction
       SET status = v_target_status
     WHERE transaction_id = p_transaction_id;
    PERFORM set_config('mulewatch.phase2_change_reason', '', TRUE);
END;
$$;

-- ------------------------------------------------------------
-- FEATURE 3: RECURSIVE ACCOUNT NETWORK
-- Treats stored account relationships as an undirected graph.
-- The path array prevents cycles; depth is capped at 5.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_phase2_account_network(
    p_root_account_id BIGINT,
    p_max_depth INTEGER DEFAULT 2
)
RETURNS TABLE (
    account_id BIGINT,
    account_number VARCHAR(30),
    customer_name VARCHAR(100),
    account_status VARCHAR(20),
    depth INTEGER,
    traversal_path BIGINT[]
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM account WHERE account.account_id = p_root_account_id) THEN
        RAISE EXCEPTION 'Account ID % does not exist.', p_root_account_id;
    END IF;
    IF p_max_depth < 1 OR p_max_depth > 5 THEN
        RAISE EXCEPTION 'Network depth must be between 1 and 5.';
    END IF;

    RETURN QUERY
    WITH RECURSIVE network_walk(node_id, node_depth, node_path) AS (
        SELECT p_root_account_id, 0, ARRAY[p_root_account_id]::BIGINT[]
        UNION ALL
        SELECT adjacent.neighbor_id,
               nw.node_depth + 1,
               nw.node_path || adjacent.neighbor_id
        FROM network_walk nw
        CROSS JOIN LATERAL (
            SELECT ar.target_account_id AS neighbor_id
            FROM account_relationship ar
            WHERE ar.source_account_id = nw.node_id
            UNION
            SELECT ar.source_account_id AS neighbor_id
            FROM account_relationship ar
            WHERE ar.target_account_id = nw.node_id
        ) adjacent
        WHERE nw.node_depth < LEAST(p_max_depth, 5)
          AND NOT adjacent.neighbor_id = ANY(nw.node_path)
    )
    SELECT
        ranked.account_id,
        ranked.account_number,
        ranked.customer_name,
        ranked.account_status,
        ranked.node_depth,
        ranked.node_path
    FROM (
        SELECT DISTINCT ON (a.account_id)
            a.account_id,
            a.account_number,
            c.full_name AS customer_name,
            a.status AS account_status,
            nw.node_depth,
            nw.node_path
        FROM network_walk nw
        JOIN account a ON a.account_id = nw.node_id
        JOIN customer c ON c.customer_id = a.customer_id
        ORDER BY a.account_id, nw.node_depth, cardinality(nw.node_path)
    ) ranked
    ORDER BY ranked.node_depth, ranked.account_id;
END;
$$;

-- ------------------------------------------------------------
-- FEATURE 4A: IMMUTABLE INVESTIGATION REPORT SNAPSHOTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_investigation_report (
    report_id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL,
    generated_by BIGINT,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report_data JSONB NOT NULL,
    CONSTRAINT fk_case_report_case FOREIGN KEY (case_id)
        REFERENCES fraud_case(case_id),
    CONSTRAINT fk_case_report_investigator FOREIGN KEY (generated_by)
        REFERENCES investigator(investigator_id)
);

CREATE INDEX IF NOT EXISTS idx_case_report_case_time
    ON case_investigation_report(case_id, generated_at DESC);

CREATE OR REPLACE FUNCTION fn_phase2_prevent_report_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Generated investigation reports are immutable; create a new report instead.';
END;
$$;

DROP TRIGGER IF EXISTS trg_phase2_immutable_case_report ON case_investigation_report;
CREATE TRIGGER trg_phase2_immutable_case_report
BEFORE UPDATE OR DELETE ON case_investigation_report
FOR EACH ROW
EXECUTE FUNCTION fn_phase2_prevent_report_mutation();

CREATE OR REPLACE PROCEDURE sp_phase2_generate_case_report(
    IN p_case_id BIGINT,
    IN p_generated_by BIGINT,
    INOUT p_report_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_report_data JSONB;
BEGIN
    IF p_generated_by IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM investigator
        WHERE investigator_id = p_generated_by AND status = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'Active investigator ID % does not exist.', p_generated_by;
    END IF;

    SELECT jsonb_build_object(
        'case', to_jsonb(fc),
        'account', to_jsonb(a),
        'customer', to_jsonb(c),
        'investigator', (
            SELECT to_jsonb(i) FROM investigator i
            WHERE i.investigator_id = fc.investigator_id
        ),
        'alert', (
            SELECT to_jsonb(fa) FROM fraud_alert fa
            WHERE fa.alert_id = fc.alert_id
        ),
        'transactions', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'transaction_id', t.transaction_id,
                'txn_time', t.txn_time,
                'amount', t.amount,
                'transaction_type', t.transaction_type,
                'channel', t.channel,
                'status', t.status,
                'sender_account_id', t.sender_account_id,
                'receiver_account_id', t.receiver_account_id,
                'link_reason', ct.link_reason
            ) ORDER BY t.txn_time)
            FROM case_transaction ct
            JOIN transaction t ON t.transaction_id = ct.transaction_id
            WHERE ct.case_id = fc.case_id
        ), '[]'::JSONB),
        'notes', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'note_id', cn.note_id,
                'note_text', cn.note_text,
                'created_at', cn.created_at,
                'investigator_name', i.full_name
            ) ORDER BY cn.created_at)
            FROM case_note cn
            LEFT JOIN investigator i ON i.investigator_id = cn.investigator_id
            WHERE cn.case_id = fc.case_id
        ), '[]'::JSONB),
        'status_history', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'history_id', h.history_id,
                'old_status', h.old_status,
                'new_status', h.new_status,
                'changed_at', h.changed_at,
                'change_reason', h.change_reason,
                'changed_by_name', i.full_name
            ) ORDER BY h.changed_at)
            FROM case_status_history h
            LEFT JOIN investigator i ON i.investigator_id = h.changed_by
            WHERE h.case_id = fc.case_id
        ), '[]'::JSONB),
        'generated_at', CURRENT_TIMESTAMP
    )
    INTO v_report_data
    FROM fraud_case fc
    JOIN account a ON a.account_id = fc.account_id
    JOIN customer c ON c.customer_id = a.customer_id
    WHERE fc.case_id = p_case_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Fraud case ID % does not exist.', p_case_id;
    END IF;

    INSERT INTO case_investigation_report(case_id, generated_by, report_data)
    VALUES (p_case_id, p_generated_by, v_report_data)
    RETURNING report_id INTO p_report_id;
END;
$$;

CREATE OR REPLACE FUNCTION fn_phase2_get_case_report(p_report_id BIGINT)
RETURNS TABLE (
    report_id BIGINT,
    case_id BIGINT,
    generated_by BIGINT,
    generated_at TIMESTAMP,
    report_data JSONB
)
LANGUAGE SQL
STABLE
AS $$
    SELECT r.report_id, r.case_id, r.generated_by, r.generated_at, r.report_data
    FROM case_investigation_report r
    WHERE r.report_id = p_report_id;
$$;

-- ------------------------------------------------------------
-- OBJECT INVENTORY FOR PHASE 2 EVALUATION
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public'
  AND table_name = 'vw_phase2_transaction_explorer';

SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'fn_phase2_audit_transaction_status',
      'sp_phase2_update_transaction_status',
      'fn_phase2_account_network',
      'fn_phase2_prevent_report_mutation',
      'sp_phase2_generate_case_report',
      'fn_phase2_get_case_report'
  )
ORDER BY routine_name;

SELECT trigger_name, event_object_table, action_timing, event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN (
      'trg_phase2_transaction_status_audit',
      'trg_phase2_immutable_case_report'
  )
ORDER BY trigger_name;
