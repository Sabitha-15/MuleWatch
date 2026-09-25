-- ============================================================
-- MuleWatch - PostgreSQL Procedures
-- File: 07_procedures.sql
-- Database: PostgreSQL
--
-- Purpose:
--   1. Open fraud investigation cases
--   2. Close fraud investigation cases
--   3. Refresh suspicious account relationships
--   4. Perform periodic cursor-based risk review
-- ============================================================


-- ============================================================
-- SECTION 1: OPEN FRAUD CASE
-- ============================================================

-- ------------------------------------------------------------
-- 1.1 sp_open_fraud_case
--
-- Workflow:
--
--     Fraud Alert
--          ↓
--     Validate alert
--          ↓
--     Validate investigator
--          ↓
--     Create fraud case
--          ↓
--     Automatically link alert transaction
--
-- The procedure returns the newly created case ID through
-- the INOUT parameter p_case_id.
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE sp_open_fraud_case(
    IN p_alert_id BIGINT,
    IN p_investigator_id BIGINT,
    IN p_case_title VARCHAR(200),
    IN p_case_description TEXT,
    IN p_priority VARCHAR(20),
    INOUT p_case_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_account_id BIGINT;
    v_transaction_id BIGINT;
    v_alert_status VARCHAR(20);
    v_investigator_status VARCHAR(20);
BEGIN

    -- --------------------------------------------------------
    -- Find the account, alert status and transaction related
    -- to the selected fraud alert.
    -- --------------------------------------------------------

    SELECT
        fa.account_id,
        fa.alert_status,
        ra.transaction_id
    INTO
        v_account_id,
        v_alert_status,
        v_transaction_id

    FROM fraud_alert fa

    JOIN risk_assessment ra
        ON ra.risk_assessment_id = fa.risk_assessment_id

    WHERE fa.alert_id = p_alert_id;


    -- --------------------------------------------------------
    -- Validate alert existence
    -- --------------------------------------------------------

    IF v_account_id IS NULL THEN

        RAISE EXCEPTION
            'Fraud alert ID % does not exist',
            p_alert_id;

    END IF;


    -- --------------------------------------------------------
    -- Only OPEN alerts can generate new cases.
    -- --------------------------------------------------------

    IF v_alert_status <> 'OPEN' THEN

        RAISE EXCEPTION
            'Cannot open case: alert % has status %',
            p_alert_id,
            v_alert_status;

    END IF;


    -- --------------------------------------------------------
    -- Validate investigator existence and status.
    -- --------------------------------------------------------

    SELECT status
    INTO v_investigator_status

    FROM investigator

    WHERE investigator_id = p_investigator_id;


    IF v_investigator_status IS NULL THEN

        RAISE EXCEPTION
            'Investigator ID % does not exist',
            p_investigator_id;

    END IF;


    IF v_investigator_status <> 'ACTIVE' THEN

        RAISE EXCEPTION
            'Cannot assign case: investigator % has status %',
            p_investigator_id,
            v_investigator_status;

    END IF;


    -- --------------------------------------------------------
    -- Prevent multiple active cases for the same alert.
    -- --------------------------------------------------------

    IF EXISTS (
        SELECT 1
        FROM fraud_case
        WHERE alert_id = p_alert_id
          AND case_status <> 'CLOSED'
    ) THEN

        RAISE EXCEPTION
            'An active fraud case already exists for alert %',
            p_alert_id;

    END IF;


    -- --------------------------------------------------------
    -- Validate priority.
    -- --------------------------------------------------------

    IF p_priority NOT IN (
        'LOW',
        'MEDIUM',
        'HIGH',
        'CRITICAL'
    ) THEN

        RAISE EXCEPTION
            'Invalid priority %. Use LOW, MEDIUM, HIGH, or CRITICAL',
            p_priority;

    END IF;


    -- --------------------------------------------------------
    -- Create the fraud case.
    -- --------------------------------------------------------

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
        p_alert_id,
        v_account_id,
        p_investigator_id,
        p_case_title,
        p_case_description,
        'OPEN',
        p_priority
    )
    RETURNING case_id
    INTO p_case_id;


    -- --------------------------------------------------------
    -- Automatically link the transaction that generated
    -- the fraud alert.
    -- --------------------------------------------------------

    IF v_transaction_id IS NOT NULL THEN

        INSERT INTO case_transaction (
            case_id,
            transaction_id,
            link_reason
        )
        VALUES (
            p_case_id,
            v_transaction_id,
            'Automatically linked from fraud alert'
        )
        ON CONFLICT (
            case_id,
            transaction_id
        )
        DO NOTHING;

    END IF;


    RAISE NOTICE
        'Fraud case % opened successfully for alert %',
        p_case_id,
        p_alert_id;

END;
$$;


-- ============================================================
-- SECTION 2: CLOSE FRAUD CASE
-- ============================================================

-- ------------------------------------------------------------
-- 2.1 sp_close_fraud_case
--
-- Workflow:
--
--     Existing case
--          ↓
--     Validate case
--          ↓
--     Validate investigator
--          ↓
--     Change status → CLOSED
--          ↓
--     Record closure time
--          ↓
--     Trigger records status history
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE sp_close_fraud_case(
    IN p_case_id BIGINT,
    IN p_investigator_id BIGINT,
    IN p_closure_reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_case_status VARCHAR(30);
    v_investigator_status VARCHAR(20);
BEGIN

    -- --------------------------------------------------------
    -- Find case status.
    -- --------------------------------------------------------

    SELECT case_status
    INTO v_case_status

    FROM fraud_case

    WHERE case_id = p_case_id;


    -- --------------------------------------------------------
    -- Validate case existence.
    -- --------------------------------------------------------

    IF v_case_status IS NULL THEN

        RAISE EXCEPTION
            'Fraud case ID % does not exist',
            p_case_id;

    END IF;


    -- --------------------------------------------------------
    -- Prevent closing an already closed case.
    -- --------------------------------------------------------

    IF v_case_status = 'CLOSED' THEN

        RAISE EXCEPTION
            'Fraud case % is already closed',
            p_case_id;

    END IF;


    -- --------------------------------------------------------
    -- Validate investigator.
    -- --------------------------------------------------------

    SELECT status
    INTO v_investigator_status

    FROM investigator

    WHERE investigator_id = p_investigator_id;


    IF v_investigator_status IS NULL THEN

        RAISE EXCEPTION
            'Investigator ID % does not exist',
            p_investigator_id;

    END IF;


    IF v_investigator_status <> 'ACTIVE' THEN

        RAISE EXCEPTION
            'Cannot close case: investigator % has status %',
            p_investigator_id,
            v_investigator_status;

    END IF;


    -- --------------------------------------------------------
    -- Close the case.
    --
    -- The trg_case_status_history trigger will automatically
    -- create the audit-history record.
    -- --------------------------------------------------------

    UPDATE fraud_case

    SET
        case_status = 'CLOSED',
        closed_at = CURRENT_TIMESTAMP,
        investigator_id = p_investigator_id,

        case_description =
            CASE

                WHEN p_closure_reason IS NULL
                    THEN case_description

                WHEN case_description IS NULL
                    THEN
                        'Closure reason: '
                        || p_closure_reason

                ELSE
                    case_description
                    || E'\nClosure reason: '
                    || p_closure_reason

            END

    WHERE case_id = p_case_id;


    RAISE NOTICE
        'Fraud case % closed successfully',
        p_case_id;

END;
$$;


-- ============================================================
-- SECTION 3: REFRESH ACCOUNT RELATIONSHIPS
-- ============================================================

-- ------------------------------------------------------------
-- 3.1 sp_refresh_account_relationships
--
-- Detects relationships between accounts using transaction
-- behaviour.
--
-- Relationship types generated:
--
--   DIRECT_TRANSFER
--   COMMON_BENEFICIARY
--
-- Existing manually defined relationships such as:
--
--   SHARED_DEVICE
--   SHARED_IP
--   NETWORK_LINK
--
-- are preserved.
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE sp_refresh_account_relationships()
LANGUAGE plpgsql
AS $$
BEGIN

    -- --------------------------------------------------------
    -- Remove previously generated relationship types.
    -- --------------------------------------------------------

    DELETE FROM account_relationship

    WHERE relationship_type IN (
        'DIRECT_TRANSFER',
        'COMMON_BENEFICIARY'
    );


    -- --------------------------------------------------------
    -- Detect DIRECT_TRANSFER relationships.
    --
    -- Confidence increases when two accounts transact
    -- repeatedly.
    -- --------------------------------------------------------

    INSERT INTO account_relationship (
        source_account_id,
        target_account_id,
        relationship_type,
        confidence_score,
        notes
    )

    SELECT
        t.sender_account_id,
        t.receiver_account_id,

        'DIRECT_TRANSFER',

        LEAST(
            100,
            50 + (COUNT(*) * 10)
        )::NUMERIC(5,2),

        'Automatically detected from successful transactions'

    FROM transaction t

    WHERE t.status = 'SUCCESS'
      AND t.transaction_type = 'TRANSFER'
      AND t.sender_account_id <> t.receiver_account_id

    GROUP BY
        t.sender_account_id,
        t.receiver_account_id;


    -- --------------------------------------------------------
    -- Detect COMMON_BENEFICIARY relationships.
    --
    -- Two accounts can become connected when they interact
    -- through the same beneficiary.
    -- --------------------------------------------------------

    INSERT INTO account_relationship (
        source_account_id,
        target_account_id,
        relationship_type,
        confidence_score,
        notes
    )

    SELECT DISTINCT
        a1.account_id,
        a2.account_id,

        'COMMON_BENEFICIARY',

        70.00,

        'Automatically detected from shared beneficiary'

    FROM beneficiary b

    JOIN account a1
        ON a1.account_id = b.account_id

    JOIN transaction t1
        ON t1.beneficiary_id = b.beneficiary_id

    JOIN account a2
        ON a2.account_id = t1.sender_account_id

    WHERE a1.account_id <> a2.account_id
      AND t1.status = 'SUCCESS'

    ON CONFLICT DO NOTHING;


    RAISE NOTICE
        'Account relationships refreshed successfully';

END;
$$;


-- ============================================================
-- SECTION 4: PERIODIC RISK REVIEW USING CURSOR
-- ============================================================

-- ------------------------------------------------------------
-- 4.1 sp_periodic_risk_review
--
-- Demonstrates a PostgreSQL cursor for procedural processing.
--
-- The procedure checks the latest risk assessment for each
-- account and reports accounts whose risk score is >= 80.
--
-- Set-based SQL should normally be preferred for large-scale
-- operations, but this cursor demonstrates procedural
-- database programming required by the project.
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE sp_periodic_risk_review()
LANGUAGE plpgsql
AS $$
DECLARE

    v_account_id BIGINT;
    v_account_number VARCHAR(30);

    v_risk_score NUMERIC(5,2);
    v_risk_level VARCHAR(20);

    v_alert_count INTEGER;


    -- --------------------------------------------------------
    -- Cursor selects the latest risk assessment for each
    -- account.
    -- --------------------------------------------------------

    risk_cursor CURSOR FOR

        SELECT DISTINCT ON (ra.account_id)

            ra.account_id,
            a.account_number,
            ra.risk_score,
            ra.risk_level

        FROM risk_assessment ra

        JOIN account a
            ON a.account_id = ra.account_id

        ORDER BY
            ra.account_id,
            ra.assessed_at DESC,
            ra.risk_assessment_id DESC;

BEGIN

    -- --------------------------------------------------------
    -- Open cursor.
    -- --------------------------------------------------------

    OPEN risk_cursor;


    -- --------------------------------------------------------
    -- Process each account.
    -- --------------------------------------------------------

    LOOP

        FETCH risk_cursor

        INTO
            v_account_id,
            v_account_number,
            v_risk_score,
            v_risk_level;


        -- Stop when there are no more rows.
        EXIT WHEN NOT FOUND;


        -- ----------------------------------------------------
        -- Only investigate high-risk accounts.
        -- ----------------------------------------------------

        IF v_risk_score >= 80 THEN

            SELECT COUNT(*)
            INTO v_alert_count

            FROM fraud_alert

            WHERE account_id = v_account_id
              AND alert_status IN (
                  'OPEN',
                  'UNDER_REVIEW'
              );


            RAISE NOTICE
                'Periodic review: Account %, Risk %, Level %, Open Alerts %',
                v_account_number,
                v_risk_score,
                v_risk_level,
                v_alert_count;

        END IF;

    END LOOP;


    -- --------------------------------------------------------
    -- Close cursor.
    -- --------------------------------------------------------

    CLOSE risk_cursor;


    RAISE NOTICE
        'Periodic risk review completed successfully';

END;
$$;


-- ============================================================
-- SECTION 5: VERIFY PROCEDURES
-- ============================================================

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


-- ============================================================
-- SECTION 6: VERIFY PROCEDURES FROM PG_PROCEDURES
-- ============================================================

SELECT
    p.proname AS procedure_name

FROM pg_proc p

JOIN pg_namespace n
    ON n.oid = p.pronamespace

WHERE n.nspname = 'public'

  AND p.proname IN (
      'sp_open_fraud_case',
      'sp_close_fraud_case',
      'sp_refresh_account_relationships',
      'sp_periodic_risk_review'
  )

ORDER BY p.proname;


-- ============================================================
-- END OF 07_procedures.sql
-- ============================================================