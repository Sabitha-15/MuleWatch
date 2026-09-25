-- ============================================================
-- MuleWatch - PostgreSQL Triggers
-- File: 06_triggers.sql
-- Database: PostgreSQL
--
-- Purpose:
--   1. Automatically create fraud alerts for high-risk scores
--   2. Maintain fraud case status history
--   3. Prevent self-account relationships
--   4. Validate transaction account status
-- ============================================================


-- ============================================================
-- SECTION 1: AUTOMATIC FRAUD ALERT TRIGGER
-- ============================================================

-- ------------------------------------------------------------
-- 1.1 Trigger Function: trg_create_fraud_alert
--
-- When a new risk assessment is inserted:
--
--     risk_score >= 85
--             ↓
--     automatic fraud alert
--
-- Risk 90-100 -> CRITICAL alert
-- Risk 85-89  -> HIGH alert
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trg_create_fraud_alert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    IF NEW.risk_score >= 85 THEN

        -- Prevent duplicate alerts for the same assessment.
        IF NOT EXISTS (
            SELECT 1
            FROM fraud_alert
            WHERE risk_assessment_id = NEW.risk_assessment_id
        ) THEN

            INSERT INTO fraud_alert (
                risk_assessment_id,
                account_id,
                alert_level,
                alert_status,
                alert_message
            )
            VALUES (
                NEW.risk_assessment_id,
                NEW.account_id,

                CASE
                    WHEN fn_alert_level(NEW.risk_score) = 'CRITICAL'
                    THEN 'CRITICAL'
                    ELSE 'HIGH'
                END,

                'OPEN',

                FORMAT(
                    'Automatic fraud alert generated for risk score %s (%s)',
                    NEW.risk_score::TEXT,
                    fn_alert_level(NEW.risk_score)
                )
            );

        END IF;

    END IF;

    RETURN NEW;

END;
$$;


-- Remove old trigger if it already exists.
DROP TRIGGER IF EXISTS trg_create_fraud_alert
ON risk_assessment;


-- Create the trigger.
CREATE TRIGGER trg_create_fraud_alert
AFTER INSERT
ON risk_assessment
FOR EACH ROW
EXECUTE FUNCTION trg_create_fraud_alert();


-- ============================================================
-- SECTION 2: FRAUD CASE STATUS HISTORY
-- ============================================================

-- ------------------------------------------------------------
-- 2.1 Trigger Function: trg_case_status_history
--
-- Whenever a fraud case changes status:
--
--     OPEN
--       ↓
--     UNDER_REVIEW
--       ↓
--     ESCALATED / CLOSED
--
-- The old and new status are automatically recorded in
-- CASE_STATUS_HISTORY.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trg_case_status_history()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    IF OLD.case_status IS DISTINCT FROM NEW.case_status THEN

        INSERT INTO case_status_history (
            case_id,
            old_status,
            new_status,
            changed_by,
            change_reason
        )
        VALUES (
            NEW.case_id,
            OLD.case_status,
            NEW.case_status,
            NEW.investigator_id,
            'Case status changed'
        );

    END IF;

    RETURN NEW;

END;
$$;


-- Remove old trigger if it already exists.
DROP TRIGGER IF EXISTS trg_case_status_history
ON fraud_case;


-- Create the trigger.
CREATE TRIGGER trg_case_status_history
AFTER UPDATE OF case_status
ON fraud_case
FOR EACH ROW
EXECUTE FUNCTION trg_case_status_history();


-- ============================================================
-- SECTION 3: PREVENT SELF ACCOUNT RELATIONSHIP
-- ============================================================

-- ------------------------------------------------------------
-- 3.1 Trigger Function: trg_prevent_self_relationship
--
-- Prevents invalid relationships such as:
--
--     Account 5 → Account 5
--
-- An account cannot be related to itself.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trg_prevent_self_relationship()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    IF NEW.source_account_id = NEW.target_account_id THEN

        RAISE EXCEPTION
            'Invalid account relationship: source account % cannot be related to itself',
            NEW.source_account_id;

    END IF;

    RETURN NEW;

END;
$$;


-- Remove old trigger if it already exists.
DROP TRIGGER IF EXISTS trg_prevent_self_relationship
ON account_relationship;


-- Create the trigger.
CREATE TRIGGER trg_prevent_self_relationship
BEFORE INSERT
ON account_relationship
FOR EACH ROW
EXECUTE FUNCTION trg_prevent_self_relationship();


-- ============================================================
-- SECTION 4: TRANSACTION VALIDATION
-- ============================================================

-- ------------------------------------------------------------
-- 4.1 Trigger Function: trg_validate_transaction
--
-- Before inserting or updating a transaction:
--
-- 1. Sender account must exist.
-- 2. Receiver account must exist.
-- 3. Sender account must be ACTIVE.
-- 4. Receiver account must be ACTIVE.
--
-- This prevents transactions involving blocked or closed
-- accounts.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION trg_validate_transaction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_sender_status VARCHAR(20);
    v_receiver_status VARCHAR(20);
BEGIN

    -- --------------------------------------------------------
    -- Get sender account status
    -- --------------------------------------------------------

    SELECT status
    INTO v_sender_status
    FROM account
    WHERE account_id = NEW.sender_account_id;


    -- --------------------------------------------------------
    -- Get receiver account status
    -- --------------------------------------------------------

    SELECT status
    INTO v_receiver_status
    FROM account
    WHERE account_id = NEW.receiver_account_id;


    -- --------------------------------------------------------
    -- Validate sender existence
    -- --------------------------------------------------------

    IF v_sender_status IS NULL THEN

        RAISE EXCEPTION
            'Transaction rejected: sender account % does not exist',
            NEW.sender_account_id;

    END IF;


    -- --------------------------------------------------------
    -- Validate receiver existence
    -- --------------------------------------------------------

    IF v_receiver_status IS NULL THEN

        RAISE EXCEPTION
            'Transaction rejected: receiver account % does not exist',
            NEW.receiver_account_id;

    END IF;


    -- --------------------------------------------------------
    -- Validate sender status
    -- --------------------------------------------------------

    IF v_sender_status <> 'ACTIVE' THEN

        RAISE EXCEPTION
            'Transaction rejected: sender account % has status %',
            NEW.sender_account_id,
            v_sender_status;

    END IF;


    -- --------------------------------------------------------
    -- Validate receiver status
    -- --------------------------------------------------------

    IF v_receiver_status <> 'ACTIVE' THEN

        RAISE EXCEPTION
            'Transaction rejected: receiver account % has status %',
            NEW.receiver_account_id,
            v_receiver_status;

    END IF;


    RETURN NEW;

END;
$$;


-- Remove old trigger if it already exists.
DROP TRIGGER IF EXISTS trg_validate_transaction
ON transaction;


-- Create the trigger.
CREATE TRIGGER trg_validate_transaction
BEFORE INSERT OR UPDATE
ON transaction
FOR EACH ROW
EXECUTE FUNCTION trg_validate_transaction();


-- ============================================================
-- SECTION 5: VERIFY TRIGGERS
-- ============================================================

-- ------------------------------------------------------------
-- 5.1 Verify trigger definitions
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
-- 5.2 Verify trigger functions
-- ============================================================

SELECT
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'trg_create_fraud_alert',
      'trg_case_status_history',
      'trg_prevent_self_relationship',
      'trg_validate_transaction'
  )
ORDER BY routine_name;


-- ============================================================
-- END OF 06_triggers.sql
-- ============================================================