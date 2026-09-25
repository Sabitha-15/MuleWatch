-- ============================================================
-- MuleWatch - PL/pgSQL Functions
-- File: 05_functions.sql
-- Database: PostgreSQL
--
-- Purpose:
--   1. Classify risk scores into alert levels
--   2. Generate an account-level risk summary
--   3. Calculate suspicious transaction amount for a case
-- ============================================================


-- ============================================================
-- SECTION 1: RISK SCORE CLASSIFICATION
-- ============================================================

-- ------------------------------------------------------------
-- 1.1 fn_alert_level
--
-- Converts a numerical risk score into a risk category.
--
-- 0  - 39  -> LOW
-- 40 - 79  -> MEDIUM
-- 80 - 89  -> HIGH
-- 90 - 100 -> CRITICAL
--
-- Invalid scores and NULL values are rejected.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_alert_level(
    p_risk_score NUMERIC
)
RETURNS VARCHAR(20)
LANGUAGE plpgsql
AS $$
BEGIN

    IF p_risk_score IS NULL THEN
        RAISE EXCEPTION
            'Risk score cannot be NULL';
    END IF;


    IF p_risk_score < 0
       OR p_risk_score > 100 THEN

        RAISE EXCEPTION
            'Invalid risk score: %. Risk score must be between 0 and 100.',
            p_risk_score;

    END IF;


    IF p_risk_score < 40 THEN
        RETURN 'LOW';

    ELSIF p_risk_score < 80 THEN
        RETURN 'MEDIUM';

    ELSIF p_risk_score < 90 THEN
        RETURN 'HIGH';

    ELSE
        RETURN 'CRITICAL';
    END IF;

END;
$$;


-- ============================================================
-- SECTION 2: ACCOUNT RISK SUMMARY
-- ============================================================

-- ------------------------------------------------------------
-- 2.1 fn_account_risk_summary
--
-- Generates an investigation summary for one account.
--
-- Returns:
--   account_id
--   account_number
--   customer_name
--   latest_risk_score
--   alert_count
--   recent_incoming_total
--   recent_outgoing_total
--   recent_suspicious_transaction_count
--
-- "Recent" means the last 30 days relative to the latest
-- transaction time in the database.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_account_risk_summary(
    p_account_id BIGINT
)
RETURNS TABLE (
    account_id BIGINT,
    account_number VARCHAR(30),
    customer_name VARCHAR(100),
    latest_risk_score NUMERIC(5,2),
    alert_count BIGINT,
    recent_incoming_total NUMERIC(15,2),
    recent_outgoing_total NUMERIC(15,2),
    recent_suspicious_transaction_count BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_latest_transaction_time TIMESTAMP;
BEGIN

    -- --------------------------------------------------------
    -- Validate account
    -- --------------------------------------------------------

    IF NOT EXISTS (
        SELECT 1
        FROM account
        WHERE account.account_id = p_account_id
    ) THEN

        RAISE EXCEPTION
            'Account ID % does not exist',
            p_account_id;

    END IF;


    -- --------------------------------------------------------
    -- Find the latest transaction time in the database.
    -- This gives us a stable reference point for the
    -- 30-day analysis window.
    -- --------------------------------------------------------

    SELECT MAX(t.txn_time)
    INTO v_latest_transaction_time
    FROM transaction t;


    -- --------------------------------------------------------
    -- Return the account-level investigation summary.
    -- --------------------------------------------------------

    RETURN QUERY

    SELECT
        a.account_id,
        a.account_number,
        c.full_name AS customer_name,

        -- Latest risk score
        latest_risk.risk_score AS latest_risk_score,

        -- Number of alerts
        COALESCE(
            alert_summary.alert_count,
            0
        ) AS alert_count,

        -- Incoming money during the recent period
        COALESCE(
            SUM(
                CASE
                    WHEN t.receiver_account_id = a.account_id
                     AND t.status = 'SUCCESS'
                    THEN t.amount
                    ELSE 0
                END
            ),
            0
        )::NUMERIC(15,2) AS recent_incoming_total,

        -- Outgoing money during the recent period
        COALESCE(
            SUM(
                CASE
                    WHEN t.sender_account_id = a.account_id
                     AND t.status = 'SUCCESS'
                    THEN t.amount
                    ELSE 0
                END
            ),
            0
        )::NUMERIC(15,2) AS recent_outgoing_total,

        -- Number of distinct suspicious transactions
        COALESCE(
            COUNT(
                DISTINCT CASE
                    WHEN ra.risk_score >= 80
                    THEN t.transaction_id
                END
            ),
            0
        ) AS recent_suspicious_transaction_count

    FROM account a

    JOIN customer c
        ON c.customer_id = a.customer_id

    -- Latest risk assessment for this account
    LEFT JOIN LATERAL (
        SELECT
            ra.risk_score
        FROM risk_assessment ra
        WHERE ra.account_id = a.account_id
        ORDER BY
            ra.assessed_at DESC,
            ra.risk_assessment_id DESC
        LIMIT 1
    ) latest_risk
        ON TRUE

    -- Count alerts separately so transaction joins do not
    -- multiply the alert count.
    LEFT JOIN (
        SELECT
            fa.account_id,
            COUNT(*) AS alert_count
        FROM fraud_alert fa
        GROUP BY fa.account_id
    ) alert_summary
        ON alert_summary.account_id = a.account_id

    -- Account's incoming and outgoing transactions
    LEFT JOIN transaction t
        ON (
            t.sender_account_id = a.account_id
            OR t.receiver_account_id = a.account_id
        )
        AND t.txn_time >=
            v_latest_transaction_time - INTERVAL '30 days'
        AND t.txn_time <=
            v_latest_transaction_time

    -- Risk information for suspicious transaction analysis
    LEFT JOIN risk_assessment ra
        ON ra.transaction_id = t.transaction_id
        AND ra.account_id = a.account_id

    WHERE a.account_id = p_account_id

    GROUP BY
        a.account_id,
        a.account_number,
        c.full_name,
        latest_risk.risk_score,
        alert_summary.alert_count;

END;
$$;


-- ============================================================
-- SECTION 3: CASE SUSPICIOUS AMOUNT
-- ============================================================

-- ------------------------------------------------------------
-- 3.1 fn_case_suspicious_amount
--
-- Calculates the total transaction amount linked to a
-- particular fraud case.
--
-- The case_transaction table connects fraud cases with
-- suspicious transactions.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_case_suspicious_amount(
    p_case_id BIGINT
)
RETURNS NUMERIC(15,2)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_amount NUMERIC(15,2);
BEGIN

    -- --------------------------------------------------------
    -- Validate case
    -- --------------------------------------------------------

    IF NOT EXISTS (
        SELECT 1
        FROM fraud_case
        WHERE case_id = p_case_id
    ) THEN

        RAISE EXCEPTION
            'Fraud case ID % does not exist',
            p_case_id;

    END IF;


    -- --------------------------------------------------------
    -- Calculate total suspicious transaction amount.
    -- --------------------------------------------------------

    SELECT
        COALESCE(
            SUM(t.amount),
            0
        )
    INTO v_total_amount

    FROM case_transaction ct

    JOIN transaction t
        ON t.transaction_id = ct.transaction_id

    WHERE ct.case_id = p_case_id;


    RETURN v_total_amount;

END;
$$;


-- ============================================================
-- SECTION 4: FUNCTION VERIFICATION
-- ============================================================


-- ------------------------------------------------------------
-- 4.1 Test risk classification
-- ------------------------------------------------------------

SELECT
    fn_alert_level(25) AS low_test,
    fn_alert_level(65) AS medium_test,
    fn_alert_level(85) AS high_test,
    fn_alert_level(95) AS critical_test;


-- ------------------------------------------------------------
-- 4.2 Test account risk summary
-- ------------------------------------------------------------

SELECT *
FROM fn_account_risk_summary(5);


-- ------------------------------------------------------------
-- 4.3 Test case suspicious amount
-- ------------------------------------------------------------

SELECT
    fn_case_suspicious_amount(1)
        AS case_1_suspicious_amount;


-- ------------------------------------------------------------
-- 4.4 Verify functions exist
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


-- ============================================================
-- END OF 05_functions.sql
-- ============================================================