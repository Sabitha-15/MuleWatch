-- ============================================================
-- MuleWatch - Database Test Suite
-- File: 08_tests.sql
-- Database: PostgreSQL
--
-- Purpose:
--   Verify functions, triggers and procedures.
--
-- Important:
--   Tests that modify database data are executed inside
--   transactions and rolled back so the test data does not
--   permanently change the database.
-- ============================================================


-- ============================================================
-- SECTION 1: FUNCTION TESTS
-- ============================================================


-- ------------------------------------------------------------
-- 1.1 Test fn_alert_level()
-- ------------------------------------------------------------

SELECT
    fn_alert_level(25) AS low_result,
    fn_alert_level(65) AS medium_result,
    fn_alert_level(85) AS high_result,
    fn_alert_level(95) AS critical_result;


-- ------------------------------------------------------------
-- 1.2 Test account risk summary
-- ------------------------------------------------------------

SELECT *
FROM fn_account_risk_summary(5);


-- ------------------------------------------------------------
-- 1.3 Test suspicious case amount
-- ------------------------------------------------------------

SELECT
    fn_case_suspicious_amount(1)
        AS case_1_suspicious_amount;


-- ============================================================
-- SECTION 2: FUNCTION EXCEPTION TESTS
-- ============================================================


-- ------------------------------------------------------------
-- 2.1 Invalid risk score
-- ------------------------------------------------------------

DO $$
BEGIN

    BEGIN

        PERFORM fn_alert_level(101);

        RAISE EXCEPTION
            'TEST FAILED: fn_alert_level() accepted invalid score';

    EXCEPTION
        WHEN OTHERS THEN

            IF SQLERRM LIKE 'Invalid risk score:%' THEN

                RAISE NOTICE
                    'TEST PASSED: Invalid risk score rejected';

            ELSE

                RAISE;

            END IF;

    END;

END;
$$;


-- ------------------------------------------------------------
-- 2.2 Invalid account
-- ------------------------------------------------------------

DO $$
BEGIN

    BEGIN

        PERFORM *
        FROM fn_account_risk_summary(999999);

        RAISE EXCEPTION
            'TEST FAILED: Invalid account was accepted';

    EXCEPTION
        WHEN OTHERS THEN

            IF SQLERRM LIKE 'Account ID % does not exist' THEN

                RAISE NOTICE
                    'TEST PASSED: Invalid account rejected';

            ELSE

                RAISE;

            END IF;

    END;

END;
$$;


-- ------------------------------------------------------------
-- 2.3 Invalid fraud case
-- ------------------------------------------------------------

DO $$
BEGIN

    BEGIN

        PERFORM fn_case_suspicious_amount(999999);

        RAISE EXCEPTION
            'TEST FAILED: Invalid case was accepted';

    EXCEPTION
        WHEN OTHERS THEN

            IF SQLERRM LIKE 'Fraud case ID % does not exist' THEN

                RAISE NOTICE
                    'TEST PASSED: Invalid fraud case rejected';

            ELSE

                RAISE;

            END IF;

    END;

END;
$$;


-- ============================================================
-- SECTION 3: TRIGGER TEST - FRAUD ALERT
-- ============================================================

-- ------------------------------------------------------------
-- Insert a high-risk assessment inside a transaction.
--
-- The trigger should automatically create a fraud alert.
--
-- ROLLBACK removes the test assessment and test alert.
-- ------------------------------------------------------------

BEGIN;

INSERT INTO risk_assessment (
    account_id,
    transaction_id,
    risk_score,
    risk_level,
    model_version,
    reason
)
VALUES (
    6,
    8,
    88,
    'HIGH',
    'TEST-1.0',
    'Automated trigger test'
)
RETURNING risk_assessment_id;


SELECT
    fa.alert_id,
    fa.risk_assessment_id,
    fa.account_id,
    fa.alert_level,
    fa.alert_status,
    fa.alert_message
FROM fraud_alert fa
WHERE fa.risk_assessment_id = (
    SELECT MAX(risk_assessment_id)
    FROM risk_assessment
    WHERE model_version = 'TEST-1.0'
);

ROLLBACK;


-- ============================================================
-- SECTION 4: TRIGGER TEST - SELF RELATIONSHIP
-- ============================================================

-- ------------------------------------------------------------
-- Account 5 → Account 5 must be rejected.
-- ------------------------------------------------------------

DO $$
BEGIN

    BEGIN

        INSERT INTO account_relationship (
            source_account_id,
            target_account_id,
            relationship_type,
            confidence_score,
            notes
        )
        VALUES (
            5,
            5,
            'DIRECT_TRANSFER',
            90.00,
            'Self relationship trigger test'
        );

        RAISE EXCEPTION
            'TEST FAILED: Self relationship was accepted';

    EXCEPTION
        WHEN OTHERS THEN

            IF SQLERRM LIKE
                'Invalid account relationship:%'
            THEN

                RAISE NOTICE
                    'TEST PASSED: Self relationship rejected';

            ELSE

                RAISE;

            END IF;

    END;

END;
$$;


-- ============================================================
-- SECTION 5: TRIGGER TEST - TRANSACTION VALIDATION
-- ============================================================

-- ------------------------------------------------------------
-- Temporarily block Account 5.
-- Attempt a transaction.
-- The trigger should reject it.
-- Restore Account 5 afterwards.
-- ------------------------------------------------------------

BEGIN;

UPDATE account
SET status = 'BLOCKED'
WHERE account_id = 5;


DO $$
BEGIN

    BEGIN

        INSERT INTO transaction (
            sender_account_id,
            receiver_account_id,
            amount,
            transaction_type,
            channel,
            status,
            description
        )
        VALUES (
            5,
            7,
            2000.00,
            'TRANSFER',
            'TEST',
            'SUCCESS',
            'Transaction validation test'
        );

        RAISE EXCEPTION
            'TEST FAILED: Transaction from blocked account accepted';

    EXCEPTION
        WHEN OTHERS THEN

            IF SQLERRM LIKE
                'Transaction rejected: sender account%'
            THEN

                RAISE NOTICE
                    'TEST PASSED: Blocked sender transaction rejected';

            ELSE

                RAISE;

            END IF;

    END;

END;
$$;


ROLLBACK;


-- ============================================================
-- SECTION 6: PROCEDURE TEST - OPEN FRAUD CASE
-- ============================================================

-- ------------------------------------------------------------
-- Use an existing OPEN fraud alert.
--
-- The procedure creates a test case.
-- The entire transaction is rolled back afterwards.
-- ------------------------------------------------------------

BEGIN;

CALL sp_open_fraud_case(
    2,
    1,
    'TEST - Fraud Investigation',
    'Temporary procedure test case',
    'HIGH',
    NULL
);


SELECT
    case_id,
    alert_id,
    account_id,
    investigator_id,
    case_title,
    case_status,
    priority
FROM fraud_case
WHERE case_title = 'TEST - Fraud Investigation';


ROLLBACK;


-- ============================================================
-- SECTION 7: PROCEDURE TEST - CLOSE FRAUD CASE
-- ============================================================

-- ------------------------------------------------------------
-- Create a temporary OPEN case.
-- Then close it using the procedure.
-- Finally rollback everything.
-- ------------------------------------------------------------

BEGIN;

INSERT INTO fraud_case (
    alert_id,
    account_id,
    investigator_id,
    case_title,
    case_description,
    case_status,
    priority
)
VALUES (
    NULL,
    6,
    1,
    'TEST - Case Closure',
    'Temporary case for procedure testing',
    'OPEN',
    'HIGH'
)
RETURNING case_id;


-- The case ID above is the temporary case.
-- Close the latest test case.

DO $$
DECLARE
    v_test_case_id BIGINT;
BEGIN

    SELECT MAX(case_id)
    INTO v_test_case_id
    FROM fraud_case
    WHERE case_title = 'TEST - Case Closure';

    CALL sp_close_fraud_case(
        v_test_case_id,
        1,
        'Temporary closure test'
    );

END;
$$;


SELECT
    case_id,
    case_status,
    closed_at,
    case_description
FROM fraud_case
WHERE case_title = 'TEST - Case Closure';


ROLLBACK;


-- ============================================================
-- SECTION 8: PROCEDURE TEST - REFRESH RELATIONSHIPS
-- ============================================================

-- ------------------------------------------------------------
-- Refresh generated account relationships.
--
-- This is wrapped in a transaction so the test does not
-- permanently change the relationship table.
-- ------------------------------------------------------------

BEGIN;

CALL sp_refresh_account_relationships();


SELECT
    relationship_type,
    COUNT(*) AS relationship_count
FROM account_relationship
GROUP BY relationship_type
ORDER BY relationship_type;

ROLLBACK;


-- ============================================================
-- SECTION 9: CURSOR PROCEDURE TEST
-- ============================================================

-- ------------------------------------------------------------
-- Run periodic risk review.
--
-- High-risk accounts should produce NOTICE messages.
-- ------------------------------------------------------------

CALL sp_periodic_risk_review();


-- ============================================================
-- SECTION 10: FINAL DATABASE OBJECT AUDIT
-- ============================================================


-- ------------------------------------------------------------
-- Verify all MuleWatch functions.
-- ------------------------------------------------------------

SELECT
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'fn_alert_level',
      'fn_account_risk_summary',
      'fn_case_suspicious_amount'
  )
ORDER BY routine_name;


-- ------------------------------------------------------------
-- Verify all MuleWatch procedures.
-- ------------------------------------------------------------

SELECT
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'sp_open_fraud_case',
      'sp_close_fraud_case',
      'sp_refresh_account_relationships',
      'sp_periodic_risk_review'
  )
ORDER BY routine_name;


-- ------------------------------------------------------------
-- Verify all MuleWatch triggers.
-- ------------------------------------------------------------

SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_timing
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name IN (
      'trg_create_fraud_alert',
      'trg_case_status_history',
      'trg_prevent_self_relationship',
      'trg_validate_transaction'
  )
ORDER BY
    trigger_name,
    event_manipulation;


-- ============================================================
-- END OF 08_tests.sql
-- ============================================================