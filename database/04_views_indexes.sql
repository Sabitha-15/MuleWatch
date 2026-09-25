-- ============================================================
-- MuleWatch - Views and Indexes
-- File: 04_views_indexes.sql
-- Database: PostgreSQL
--
-- Purpose:
--   1. Create reusable investigation views
--   2. Create performance indexes
--   3. Verify that the views and indexes were created
-- ============================================================


-- ============================================================
-- SECTION 0: REMOVE EXISTING VIEWS
-- ============================================================

-- These views may already exist from earlier development/testing.
-- Dropping them first allows us to recreate them with the
-- intended column names.

DROP VIEW IF EXISTS
    vw_high_risk_accounts,
    vw_open_fraud_alerts,
    vw_case_summary,
    vw_transaction_flow;


-- ============================================================
-- SECTION 1: VIEWS
-- ============================================================


-- ------------------------------------------------------------
-- 1.1 High-Risk Accounts
--
-- Shows accounts whose latest risk assessment is HIGH or
-- CRITICAL (risk score >= 80).
--
-- Also shows:
--   - Customer name
--   - Latest risk score
--   - Number of fraud alerts
--   - Latest assessment time
-- ------------------------------------------------------------

CREATE VIEW vw_high_risk_accounts AS
SELECT
    a.account_id,
    a.account_number,
    c.full_name AS customer_name,
    latest_risk.risk_score AS latest_risk_score,
    COALESCE(alert_summary.alert_count, 0) AS alert_count,
    latest_risk.assessed_at AS latest_assessment_time

FROM account a

JOIN customer c
    ON c.customer_id = a.customer_id

JOIN LATERAL (
    SELECT
        ra.risk_score,
        ra.assessed_at
    FROM risk_assessment ra
    WHERE ra.account_id = a.account_id
    ORDER BY
        ra.assessed_at DESC,
        ra.risk_assessment_id DESC
    LIMIT 1
) latest_risk
    ON TRUE

LEFT JOIN (
    SELECT
        account_id,
        COUNT(*) AS alert_count
    FROM fraud_alert
    GROUP BY account_id
) alert_summary
    ON alert_summary.account_id = a.account_id

WHERE latest_risk.risk_score >= 80;


-- ------------------------------------------------------------
-- 1.2 Open Fraud Alerts
--
-- Shows fraud alerts that are currently:
--   OPEN
--   UNDER_REVIEW
--
-- Includes account, customer, risk assessment and
-- transaction information.
-- ------------------------------------------------------------

CREATE VIEW vw_open_fraud_alerts AS
SELECT
    fa.alert_id,
    fa.account_id,
    a.account_number,
    c.full_name AS customer_name,
    fa.alert_level,
    fa.alert_status,
    fa.alert_message,
    fa.created_at,

    ra.risk_score,
    ra.risk_level,
    ra.transaction_id,

    t.sender_account_id,
    t.receiver_account_id,
    t.amount,
    t.txn_time,
    t.transaction_type

FROM fraud_alert fa

JOIN account a
    ON a.account_id = fa.account_id

JOIN customer c
    ON c.customer_id = a.customer_id

JOIN risk_assessment ra
    ON ra.risk_assessment_id = fa.risk_assessment_id

LEFT JOIN transaction t
    ON t.transaction_id = ra.transaction_id

WHERE fa.alert_status IN (
    'OPEN',
    'UNDER_REVIEW'
);


-- ------------------------------------------------------------
-- 1.3 Case Summary
--
-- Provides an investigation-level summary.
--
-- Includes:
--   - Case information
--   - Account information
--   - Customer information
--   - Assigned investigator
--   - Number of linked transactions
--   - Total suspicious transaction amount
-- ------------------------------------------------------------

CREATE VIEW vw_case_summary AS
SELECT
    fc.case_id,
    fc.case_title,
    fc.case_status,
    fc.priority,

    fc.account_id,
    a.account_number,
    c.full_name AS customer_name,

    i.full_name AS investigator_name,

    COUNT(ct.transaction_id) AS linked_transaction_count,

    COALESCE(
        SUM(t.amount),
        0
    ) AS total_suspicious_amount,

    fc.opened_at,
    fc.closed_at

FROM fraud_case fc

JOIN account a
    ON a.account_id = fc.account_id

JOIN customer c
    ON c.customer_id = a.customer_id

LEFT JOIN investigator i
    ON i.investigator_id = fc.investigator_id

LEFT JOIN case_transaction ct
    ON ct.case_id = fc.case_id

LEFT JOIN transaction t
    ON t.transaction_id = ct.transaction_id

GROUP BY
    fc.case_id,
    fc.case_title,
    fc.case_status,
    fc.priority,
    fc.account_id,
    a.account_number,
    c.full_name,
    i.full_name,
    fc.opened_at,
    fc.closed_at;


-- ------------------------------------------------------------
-- 1.4 Transaction Flow
--
-- Simplifies money-flow analysis.
--
-- Shows:
--   Source account
--   Target account
--   Amount
--   Transaction time
--   Transaction type
--   Transaction status
--
-- This view will later support the "Trace the Money"
-- investigation feature in the frontend.
-- ------------------------------------------------------------

CREATE VIEW vw_transaction_flow AS
SELECT
    t.transaction_id,

    t.sender_account_id AS source_account_id,
    sender.account_number AS source_account_number,

    t.receiver_account_id AS target_account_id,
    receiver.account_number AS target_account_number,

    t.amount,
    t.txn_time,
    t.transaction_type,
    t.status

FROM transaction t

JOIN account sender
    ON sender.account_id = t.sender_account_id

JOIN account receiver
    ON receiver.account_id = t.receiver_account_id;


-- ============================================================
-- SECTION 2: INDEXES
-- ============================================================


-- ------------------------------------------------------------
-- 2.1 Case Transaction Lookup
--
-- Helps find all fraud cases associated with a transaction.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_case_transaction_transaction
ON case_transaction(transaction_id);


-- ------------------------------------------------------------
-- 2.2 Fraud Alert Status
--
-- Helps dashboard and investigator queries filter alerts
-- by their current status.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_fraud_alert_status
ON fraud_alert(alert_status);


-- ------------------------------------------------------------
-- 2.3 Fraud Case Status
--
-- Helps investigators quickly find OPEN, UNDER_REVIEW,
-- ESCALATED or CLOSED cases.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_fraud_case_status
ON fraud_case(case_status);


-- ------------------------------------------------------------
-- 2.4 Risk Score
--
-- Helps identify high-risk assessments.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_risk_assessment_score
ON risk_assessment(risk_score);


-- ------------------------------------------------------------
-- 2.5 Sender Account + Transaction Time
--
-- Useful for:
--   - Transaction velocity analysis
--   - Rapid movement detection
--   - Account activity analysis
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_transaction_sender_time
ON transaction(sender_account_id, txn_time);


-- ------------------------------------------------------------
-- 2.6 Transaction Time
--
-- Useful for time-range transaction analysis.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_transaction_time
ON transaction(txn_time);


-- ============================================================
-- SECTION 3: VERIFICATION QUERIES
-- ============================================================


-- ------------------------------------------------------------
-- 3.1 Verify Views
-- ------------------------------------------------------------

SELECT
    table_name
FROM information_schema.views
WHERE table_schema = 'public'
  AND table_name IN (
      'vw_high_risk_accounts',
      'vw_open_fraud_alerts',
      'vw_case_summary',
      'vw_transaction_flow'
  )
ORDER BY table_name;


-- ------------------------------------------------------------
-- 3.2 Verify Indexes
-- ------------------------------------------------------------

SELECT
    indexname,
    tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
      'idx_case_transaction_transaction',
      'idx_fraud_alert_status',
      'idx_fraud_case_status',
      'idx_risk_assessment_score',
      'idx_transaction_sender_time',
      'idx_transaction_time'
  )
ORDER BY indexname;


-- ============================================================
-- END OF 04_views_indexes.sql
-- ============================================================