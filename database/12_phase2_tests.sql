/* ============================================================
   MULEWATCH - PHASE 2 ADVANCED FEATURE TESTS
   Run after 11_phase2_advanced_features.sql.
   All data-changing tests are rolled back.
   ============================================================ */

-- 1. Transaction Explorer view
SELECT transaction_id, sender_account_number, receiver_account_number,
       amount, status, risk_score, risk_level
FROM vw_phase2_transaction_explorer
ORDER BY txn_time DESC
LIMIT 10;

-- 2. Recursive account network (change root account if needed)
SELECT * FROM fn_phase2_account_network(1, 2);

-- 3. Transaction status procedure + audit trigger (rollback test)
BEGIN;
DO $$
DECLARE
    v_transaction_id BIGINT;
BEGIN
    SELECT transaction_id INTO v_transaction_id
    FROM transaction
    WHERE status = 'PENDING'
    ORDER BY transaction_id
    LIMIT 1
    FOR UPDATE;

    IF v_transaction_id IS NULL THEN
        RAISE NOTICE 'SKIPPED: no PENDING transaction is available for the status test.';
    ELSE
        CALL sp_phase2_update_transaction_status(
            v_transaction_id,
            'SUCCESS',
            'Phase 2 rollback test'
        );
        RAISE NOTICE 'PASSED: pending transaction finalized and audit trigger executed for transaction %.', v_transaction_id;
    END IF;
END;
$$;
SELECT * FROM transaction_status_audit
ORDER BY audit_id DESC
LIMIT 5;
ROLLBACK;

-- 4. Case report procedure + report function + immutable trigger
BEGIN;
DO $$
DECLARE
    v_case_id BIGINT;
    v_report_id BIGINT;
BEGIN
    SELECT case_id INTO v_case_id
    FROM fraud_case
    ORDER BY case_id
    LIMIT 1;

    IF v_case_id IS NULL THEN
        RAISE NOTICE 'SKIPPED: no fraud case is available for report testing.';
    ELSE
        CALL sp_phase2_generate_case_report(v_case_id, NULL, v_report_id);
        RAISE NOTICE 'PASSED: generated report ID % for case %.', v_report_id, v_case_id;
        PERFORM * FROM fn_phase2_get_case_report(v_report_id);

        BEGIN
            UPDATE case_investigation_report
            SET report_data = '{}'::JSONB
            WHERE report_id = v_report_id;
            RAISE EXCEPTION 'TEST FAILED: immutable report update was accepted.';
        EXCEPTION WHEN OTHERS THEN
            IF SQLERRM LIKE 'Generated investigation reports are immutable%' THEN
                RAISE NOTICE 'PASSED: immutable report trigger rejected update.';
            ELSE
                RAISE;
            END IF;
        END;
    END IF;
END;
$$;
ROLLBACK;

-- 5. Confirm the Phase 2 objects are installed
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public' AND table_name = 'vw_phase2_transaction_explorer';

SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'fn_phase2_account_network',
    'fn_phase2_audit_transaction_status',
    'sp_phase2_update_transaction_status',
    'sp_phase2_generate_case_report',
    'fn_phase2_get_case_report',
    'fn_phase2_prevent_report_mutation'
  )
ORDER BY routine_name;

SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN (
    'trg_phase2_transaction_status_audit',
    'trg_phase2_immutable_case_report'
  )
ORDER BY trigger_name;
