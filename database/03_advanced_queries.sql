/*
=========================================================
MULEWATCH - ADVANCED SQL QUERIES
=========================================================
Purpose:
Advanced SQL queries used for fraud investigation,
transaction analysis, risk analysis, and money-flow
tracing.

Database: PostgreSQL
=========================================================
*/


/*
=========================================================
1. JOIN QUERIES
=========================================================
*/


-- 1.1 Customer → Account → Transaction analysis
-- Shows transaction activity for each customer account.

SELECT
    c.customer_id,
    c.full_name,
    a.account_id,
    a.account_number,
    t.transaction_id,
    t.amount,
    t.txn_time,
    t.transaction_type,
    t.status
FROM customer c
JOIN account a
    ON a.customer_id = c.customer_id
JOIN transaction t
    ON t.sender_account_id = a.account_id
ORDER BY
    c.customer_id,
    t.txn_time;


-- 1.2 Transaction sender and receiver details
-- Useful for investigating money movement between accounts.

SELECT
    t.transaction_id,
    t.amount,
    t.txn_time,
    t.transaction_type,
    t.status,
    sender.account_number AS sender_account,
    sender_customer.full_name AS sender_name,
    receiver.account_number AS receiver_account,
    receiver_customer.full_name AS receiver_name
FROM transaction t
JOIN account sender
    ON sender.account_id = t.sender_account_id
JOIN customer sender_customer
    ON sender_customer.customer_id = sender.customer_id
JOIN account receiver
    ON receiver.account_id = t.receiver_account_id
JOIN customer receiver_customer
    ON receiver_customer.customer_id = receiver.customer_id
ORDER BY t.txn_time;


-- 1.3 Risk assessment with account and customer information
-- Connects AI risk results to the investigated account.

SELECT
    ra.risk_assessment_id,
    a.account_number,
    c.full_name,
    ra.transaction_id,
    ra.risk_score,
    ra.risk_level,
    ra.model_version,
    ra.assessed_at,
    ra.reason
FROM risk_assessment ra
JOIN account a
    ON a.account_id = ra.account_id
JOIN customer c
    ON c.customer_id = a.customer_id
ORDER BY
    ra.risk_score DESC;

/*
=========================================================
2. AGGREGATION AND HAVING
=========================================================
*/


-- 2.1 Transaction count and total outgoing amount per account

SELECT
    a.account_id,
    a.account_number,
    COUNT(t.transaction_id) AS transaction_count,
    COALESCE(SUM(t.amount), 0) AS total_outgoing_amount,
    COALESCE(AVG(t.amount), 0) AS average_transaction_amount
FROM account a
LEFT JOIN transaction t
    ON t.sender_account_id = a.account_id
   AND t.status = 'SUCCESS'
GROUP BY
    a.account_id,
    a.account_number
ORDER BY
    total_outgoing_amount DESC;


-- 2.2 Identify accounts with high transaction activity
-- HAVING filters groups after aggregation.

SELECT
    a.account_id,
    a.account_number,
    COUNT(t.transaction_id) AS successful_transaction_count,
    SUM(t.amount) AS total_transaction_amount
FROM account a
JOIN transaction t
    ON t.sender_account_id = a.account_id
WHERE t.status = 'SUCCESS'
GROUP BY
    a.account_id,
    a.account_number
HAVING COUNT(t.transaction_id) >= 2
ORDER BY
    successful_transaction_count DESC,
    total_transaction_amount DESC;


-- 2.3 High-value transaction activity by account

SELECT
    a.account_id,
    a.account_number,
    COUNT(t.transaction_id) AS high_value_transaction_count,
    SUM(t.amount) AS high_value_total
FROM account a
JOIN transaction t
    ON t.sender_account_id = a.account_id
WHERE t.status = 'SUCCESS'
  AND t.amount >= 50000
GROUP BY
    a.account_id,
    a.account_number
HAVING SUM(t.amount) >= 50000
ORDER BY
    high_value_total DESC;


-- 2.4 Suspicious transaction count by account

SELECT
    a.account_id,
    a.account_number,
    COUNT(ra.risk_assessment_id) AS suspicious_transaction_count,
    MAX(ra.risk_score) AS maximum_risk_score,
    AVG(ra.risk_score) AS average_risk_score
FROM account a
JOIN risk_assessment ra
    ON ra.account_id = a.account_id
WHERE ra.risk_score >= 80
GROUP BY
    a.account_id,
    a.account_number
HAVING COUNT(ra.risk_assessment_id) >= 1
ORDER BY
    maximum_risk_score DESC;

/*
=========================================================
3. SUBQUERIES
=========================================================
*/


-- 3.1 Single-value subquery
-- Find transactions whose amount is greater than
-- the average transaction amount.

SELECT
    transaction_id,
    sender_account_id,
    receiver_account_id,
    amount,
    txn_time
FROM transaction
WHERE amount > (
    SELECT AVG(amount)
    FROM transaction
)
ORDER BY amount DESC;


-- 3.2 IN subquery
-- Find accounts that have at least one high-risk assessment.

SELECT
    account_id,
    account_number
FROM account
WHERE account_id IN (
    SELECT DISTINCT account_id
    FROM risk_assessment
    WHERE risk_score >= 80
)
ORDER BY account_id;


-- 3.3 ANY subquery
-- Find transactions whose amount is greater than
-- at least one high-risk transaction amount.

SELECT
    transaction_id,
    sender_account_id,
    receiver_account_id,
    amount
FROM transaction
WHERE amount > ANY (
    SELECT amount
    FROM transaction t2
    JOIN risk_assessment ra
        ON ra.transaction_id = t2.transaction_id
    WHERE ra.risk_score >= 80
)
ORDER BY amount DESC;


-- 3.4 ALL subquery
-- Find transactions whose amount is greater than
-- every high-risk transaction amount.

SELECT
    transaction_id,
    sender_account_id,
    receiver_account_id,
    amount
FROM transaction
WHERE amount > ALL (
    SELECT t2.amount
    FROM transaction t2
    JOIN risk_assessment ra
        ON ra.transaction_id = t2.transaction_id
    WHERE ra.risk_score >= 80
)
ORDER BY amount DESC;


-- 3.5 Correlated subquery
-- Find accounts whose transaction amount is greater
-- than that account's own average transaction amount.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.amount,
    t.txn_time
FROM transaction t
WHERE t.amount > (
    SELECT AVG(t2.amount)
    FROM transaction t2
    WHERE t2.sender_account_id = t.sender_account_id
)
ORDER BY
    t.sender_account_id,
    t.amount DESC;


-- 3.6 EXISTS subquery
-- Find accounts that have at least one high-risk assessment.

SELECT
    a.account_id,
    a.account_number
FROM account a
WHERE EXISTS (
    SELECT 1
    FROM risk_assessment ra
    WHERE ra.account_id = a.account_id
      AND ra.risk_score >= 80
)
ORDER BY a.account_id;

/*
=========================================================
4. COMMON TABLE EXPRESSIONS (CTEs)
=========================================================
*/


-- 4.1 Basic CTE
-- Calculate total successful outgoing amount per account.

WITH account_transaction_summary AS (
    SELECT
        sender_account_id AS account_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_outgoing_amount,
        AVG(amount) AS average_transaction_amount
    FROM transaction
    WHERE status = 'SUCCESS'
    GROUP BY sender_account_id
)
SELECT
    a.account_id,
    a.account_number,
    ats.transaction_count,
    ats.total_outgoing_amount,
    ats.average_transaction_amount
FROM account a
JOIN account_transaction_summary ats
    ON ats.account_id = a.account_id
ORDER BY ats.total_outgoing_amount DESC;


-- 4.2 CTE for high-risk accounts
-- Identify accounts whose risk score is at least 80.

WITH high_risk_accounts AS (
    SELECT
        account_id,
        MAX(risk_score) AS maximum_risk_score,
        COUNT(*) AS risk_assessment_count
    FROM risk_assessment
    GROUP BY account_id
    HAVING MAX(risk_score) >= 80
)
SELECT
    a.account_id,
    a.account_number,
    c.full_name,
    hra.maximum_risk_score,
    hra.risk_assessment_count
FROM high_risk_accounts hra
JOIN account a
    ON a.account_id = hra.account_id
JOIN customer c
    ON c.customer_id = a.customer_id
ORDER BY hra.maximum_risk_score DESC;


-- 4.3 Multi-CTE fraud investigation analysis
-- Combines transaction activity and risk information.

WITH transaction_summary AS (
    SELECT
        sender_account_id AS account_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_outgoing_amount
    FROM transaction
    WHERE status = 'SUCCESS'
    GROUP BY sender_account_id
),
risk_summary AS (
    SELECT
        account_id,
        MAX(risk_score) AS maximum_risk_score,
        AVG(risk_score) AS average_risk_score
    FROM risk_assessment
    GROUP BY account_id
)
SELECT
    a.account_id,
    a.account_number,
    COALESCE(ts.transaction_count, 0) AS transaction_count,
    COALESCE(ts.total_outgoing_amount, 0) AS total_outgoing_amount,
    COALESCE(rs.maximum_risk_score, 0) AS maximum_risk_score,
    COALESCE(rs.average_risk_score, 0) AS average_risk_score
FROM account a
LEFT JOIN transaction_summary ts
    ON ts.account_id = a.account_id
LEFT JOIN risk_summary rs
    ON rs.account_id = a.account_id
ORDER BY
    maximum_risk_score DESC,
    total_outgoing_amount DESC;


-- 4.4 CTE for suspicious transaction flow
-- Shows transactions associated with high-risk assessments.

WITH suspicious_transactions AS (
    SELECT
        t.transaction_id,
        t.sender_account_id,
        t.receiver_account_id,
        t.amount,
        t.txn_time,
        ra.risk_score,
        ra.risk_level
    FROM transaction t
    JOIN risk_assessment ra
        ON ra.transaction_id = t.transaction_id
    WHERE ra.risk_score >= 80
)
SELECT
    st.transaction_id,
    sender.account_number AS sender_account,
    receiver.account_number AS receiver_account,
    st.amount,
    st.txn_time,
    st.risk_score,
    st.risk_level
FROM suspicious_transactions st
JOIN account sender
    ON sender.account_id = st.sender_account_id
JOIN account receiver
    ON receiver.account_id = st.receiver_account_id
ORDER BY
    st.risk_score DESC,
    st.txn_time;

 /*
 =========================================================
 5. WINDOW FUNCTIONS
 =========================================================
 */


-- 5.1 ROW_NUMBER()
-- Assign a sequence number to transactions for each account.
-- Useful for identifying the first, second, third, etc. transaction.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.amount,
    t.txn_time,
    ROW_NUMBER() OVER (
        PARTITION BY t.sender_account_id
        ORDER BY t.txn_time
    ) AS transaction_sequence
FROM transaction t
ORDER BY
    t.sender_account_id,
    t.txn_time;


-- 5.2 RANK()
-- Rank transactions by amount within each sender account.
-- Transactions with the same amount receive the same rank.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.amount,
    RANK() OVER (
        PARTITION BY t.sender_account_id
        ORDER BY t.amount DESC
    ) AS amount_rank
FROM transaction t
WHERE t.status = 'SUCCESS'
ORDER BY
    t.sender_account_id,
    amount_rank;


-- 5.3 LAG()
-- Compare a transaction with the previous transaction
-- made by the same account.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.amount,
    t.txn_time,
    LAG(t.amount) OVER (
        PARTITION BY t.sender_account_id
        ORDER BY t.txn_time
    ) AS previous_transaction_amount
FROM transaction t
ORDER BY
    t.sender_account_id,
    t.txn_time;


-- 5.4 LEAD()
-- Look at the next transaction made by the same account.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.amount,
    t.txn_time,
    LEAD(t.amount) OVER (
        PARTITION BY t.sender_account_id
        ORDER BY t.txn_time
    ) AS next_transaction_amount
FROM transaction t
ORDER BY
    t.sender_account_id,
    t.txn_time;


-- 5.5 Detect sudden transaction increases
-- Compare each transaction with the previous transaction
-- made by the same account.

WITH transaction_comparison AS (
    SELECT
        t.transaction_id,
        t.sender_account_id,
        t.amount,
        t.txn_time,
        LAG(t.amount) OVER (
            PARTITION BY t.sender_account_id
            ORDER BY t.txn_time
        ) AS previous_amount
    FROM transaction t
    WHERE t.status = 'SUCCESS'
)
SELECT
    transaction_id,
    sender_account_id,
    amount,
    previous_amount,
    amount - previous_amount AS amount_difference
FROM transaction_comparison
WHERE previous_amount IS NOT NULL
  AND amount > previous_amount
ORDER BY
    amount_difference DESC;


-- 5.6 Detect rapid consecutive transactions
-- Compare the current transaction time with the previous
-- transaction time for the same account.

WITH transaction_timing AS (
    SELECT
        t.transaction_id,
        t.sender_account_id,
        t.amount,
        t.txn_time,
        LAG(t.txn_time) OVER (
            PARTITION BY t.sender_account_id
            ORDER BY t.txn_time
        ) AS previous_txn_time
    FROM transaction t
    WHERE t.status = 'SUCCESS'
)
SELECT
    transaction_id,
    sender_account_id,
    amount,
    txn_time,
    previous_txn_time,
    EXTRACT(
        EPOCH FROM (txn_time - previous_txn_time)
    ) / 60 AS minutes_since_previous_transaction
FROM transaction_timing
WHERE previous_txn_time IS NOT NULL
ORDER BY
    minutes_since_previous_transaction ASC;


-- 5.7 Highest-risk transaction for each account
-- ROW_NUMBER() allows us to select the single highest-risk
-- transaction per account.

WITH ranked_risk AS (
    SELECT
        ra.account_id,
        ra.transaction_id,
        ra.risk_score,
        ra.risk_level,
        ROW_NUMBER() OVER (
            PARTITION BY ra.account_id
            ORDER BY ra.risk_score DESC
        ) AS risk_rank
    FROM risk_assessment ra
)
SELECT
    account_id,
    transaction_id,
    risk_score,
    risk_level
FROM ranked_risk
WHERE risk_rank = 1
ORDER BY
    risk_score DESC;

/*
=========================================================
6. TIME-BASED FRAUD ANALYSIS AND TRANSACTION VELOCITY
=========================================================
*/


-- 6.1 Transactions occurring within a short time window
-- Detect transactions that happen within 10 minutes
-- of another transaction from the same account.

WITH transaction_timing AS (
    SELECT
        t.transaction_id,
        t.sender_account_id,
        t.receiver_account_id,
        t.amount,
        t.txn_time,
        LAG(t.txn_time) OVER (
            PARTITION BY t.sender_account_id
            ORDER BY t.txn_time
        ) AS previous_txn_time
    FROM transaction t
    WHERE t.status = 'SUCCESS'
)
SELECT
    transaction_id,
    sender_account_id,
    receiver_account_id,
    amount,
    txn_time,
    previous_txn_time,
    EXTRACT(
        EPOCH FROM (txn_time - previous_txn_time)
    ) / 60 AS minutes_since_previous
FROM transaction_timing
WHERE previous_txn_time IS NOT NULL
  AND txn_time - previous_txn_time <= INTERVAL '10 minutes'
ORDER BY
    sender_account_id,
    txn_time;


-- 6.2 Transaction velocity
-- Count successful transactions made by each account
-- within a 1-hour window.

SELECT
    t1.sender_account_id,
    t1.transaction_id,
    t1.txn_time,
    COUNT(t2.transaction_id) AS transactions_in_previous_hour
FROM transaction t1
JOIN transaction t2
    ON t2.sender_account_id = t1.sender_account_id
   AND t2.status = 'SUCCESS'
   AND t2.txn_time BETWEEN
       t1.txn_time - INTERVAL '1 hour'
       AND t1.txn_time
WHERE t1.status = 'SUCCESS'
GROUP BY
    t1.sender_account_id,
    t1.transaction_id,
    t1.txn_time
ORDER BY
    transactions_in_previous_hour DESC,
    t1.txn_time;


-- 6.3 High-value transactions occurring close together
-- Detect large transfers made within 15 minutes
-- by the same account.

WITH rapid_high_value_transactions AS (
    SELECT
        t.transaction_id,
        t.sender_account_id,
        t.receiver_account_id,
        t.amount,
        t.txn_time,
        LAG(t.txn_time) OVER (
            PARTITION BY t.sender_account_id
            ORDER BY t.txn_time
        ) AS previous_txn_time
    FROM transaction t
    WHERE t.status = 'SUCCESS'
      AND t.amount >= 50000
)
SELECT
    transaction_id,
    sender_account_id,
    receiver_account_id,
    amount,
    txn_time,
    previous_txn_time,
    EXTRACT(
        EPOCH FROM (txn_time - previous_txn_time)
    ) / 60 AS minutes_since_previous
FROM rapid_high_value_transactions
WHERE previous_txn_time IS NOT NULL
  AND txn_time - previous_txn_time <= INTERVAL '15 minutes'
ORDER BY
    minutes_since_previous ASC;


-- 6.4 Daily transaction activity
-- Summarize transaction volume and value for each day.

SELECT
    DATE(txn_time) AS transaction_date,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_transaction_amount,
    AVG(amount) AS average_transaction_amount
FROM transaction
WHERE status = 'SUCCESS'
GROUP BY DATE(txn_time)
ORDER BY transaction_date;


-- 6.5 Accounts with unusually high daily activity
-- Identify accounts making at least 2 successful
-- transactions on the same day.

SELECT
    sender_account_id,
    DATE(txn_time) AS transaction_date,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM transaction
WHERE status = 'SUCCESS'
GROUP BY
    sender_account_id,
    DATE(txn_time)
HAVING COUNT(*) >= 2
ORDER BY
    transaction_count DESC,
    total_amount DESC;


-- 6.6 Rapid money movement between accounts
-- Identify chains where money moves quickly from
-- one account to another.

SELECT
    t1.transaction_id AS first_transaction,
    t1.sender_account_id AS first_sender,
    t1.receiver_account_id AS intermediate_account,
    t1.amount AS first_amount,
    t1.txn_time AS first_time,
    t2.transaction_id AS second_transaction,
    t2.receiver_account_id AS final_receiver,
    t2.amount AS second_amount,
    t2.txn_time AS second_time,
    EXTRACT(
        EPOCH FROM (t2.txn_time - t1.txn_time)
    ) / 60 AS minutes_between_transactions
FROM transaction t1
JOIN transaction t2
    ON t2.sender_account_id = t1.receiver_account_id
   AND t2.txn_time > t1.txn_time
   AND t2.txn_time <= t1.txn_time + INTERVAL '30 minutes'
WHERE t1.status = 'SUCCESS'
  AND t2.status = 'SUCCESS'
ORDER BY
    minutes_between_transactions ASC;

/*
=========================================================
7. MONEY-FLOW TRACING
=========================================================
*/


-- 7.1 Direct money movement
-- Show the source and destination of every successful
-- transaction.

SELECT
    t.transaction_id,
    sender.account_number AS source_account,
    sender_customer.full_name AS source_customer,
    receiver.account_number AS destination_account,
    receiver_customer.full_name AS destination_customer,
    t.amount,
    t.txn_time,
    t.status
FROM transaction t
JOIN account sender
    ON sender.account_id = t.sender_account_id
JOIN customer sender_customer
    ON sender_customer.customer_id = sender.customer_id
JOIN account receiver
    ON receiver.account_id = t.receiver_account_id
JOIN customer receiver_customer
    ON receiver_customer.customer_id = receiver.customer_id
WHERE t.status = 'SUCCESS'
ORDER BY
    t.txn_time;


-- 7.2 Trace money leaving a particular account
-- Change the account ID to investigate a specific account.

SELECT
    t.transaction_id,
    t.sender_account_id,
    t.receiver_account_id,
    receiver.account_number AS destination_account,
    t.amount,
    t.txn_time
FROM transaction t
JOIN account receiver
    ON receiver.account_id = t.receiver_account_id
WHERE t.sender_account_id = 5
  AND t.status = 'SUCCESS'
ORDER BY
    t.txn_time;


-- 7.3 Trace money entering a particular account
-- Shows incoming transactions for an account.

SELECT
    t.transaction_id,
    sender.account_number AS source_account,
    t.receiver_account_id AS destination_account_id,
    t.amount,
    t.txn_time
FROM transaction t
JOIN account sender
    ON sender.account_id = t.sender_account_id
WHERE t.receiver_account_id = 7
  AND t.status = 'SUCCESS'
ORDER BY
    t.txn_time;


-- 7.4 Identify direct transaction chains
-- Detect A → B → C money movement.

SELECT
    t1.transaction_id AS first_transaction,
    t1.sender_account_id AS source_account,
    t1.receiver_account_id AS intermediate_account,
    t1.amount AS first_amount,
    t1.txn_time AS first_time,

    t2.transaction_id AS second_transaction,
    t2.receiver_account_id AS final_account,
    t2.amount AS second_amount,
    t2.txn_time AS second_time,

    EXTRACT(
        EPOCH FROM (t2.txn_time - t1.txn_time)
    ) / 60 AS minutes_between
FROM transaction t1
JOIN transaction t2
    ON t2.sender_account_id = t1.receiver_account_id
   AND t2.txn_time > t1.txn_time
   AND t2.txn_time <= t1.txn_time + INTERVAL '30 minutes'
WHERE t1.status = 'SUCCESS'
  AND t2.status = 'SUCCESS'
ORDER BY
    minutes_between ASC;


-- 7.5 Compare money entering and leaving each account
-- Useful for identifying accounts that quickly pass
-- money onward.

WITH incoming AS (
    SELECT
        receiver_account_id AS account_id,
        SUM(amount) AS total_incoming
    FROM transaction
    WHERE status = 'SUCCESS'
    GROUP BY receiver_account_id
),
outgoing AS (
    SELECT
        sender_account_id AS account_id,
        SUM(amount) AS total_outgoing
    FROM transaction
    WHERE status = 'SUCCESS'
    GROUP BY sender_account_id
)
SELECT
    a.account_id,
    a.account_number,
    COALESCE(i.total_incoming, 0) AS total_incoming,
    COALESCE(o.total_outgoing, 0) AS total_outgoing,
    COALESCE(i.total_incoming, 0)
        - COALESCE(o.total_outgoing, 0) AS money_difference
FROM account a
LEFT JOIN incoming i
    ON i.account_id = a.account_id
LEFT JOIN outgoing o
    ON o.account_id = a.account_id
ORDER BY
    total_incoming DESC;


-- 7.6 Identify possible pass-through accounts
-- An account is interesting when it receives money
-- and also sends money onward.

WITH incoming_accounts AS (
    SELECT DISTINCT
        receiver_account_id AS account_id
    FROM transaction
    WHERE status = 'SUCCESS'
),
outgoing_accounts AS (
    SELECT DISTINCT
        sender_account_id AS account_id
    FROM transaction
    WHERE status = 'SUCCESS'
)
SELECT
    a.account_id,
    a.account_number,
    c.full_name
FROM account a
JOIN customer c
    ON c.customer_id = a.customer_id
JOIN incoming_accounts i
    ON i.account_id = a.account_id
JOIN outgoing_accounts o
    ON o.account_id = a.account_id
ORDER BY
    a.account_id;


-- 7.7 Trace suspicious transactions through account relationships
-- Combines transaction risk with detected account links.

SELECT
    ar.relationship_id,
    ar.source_account_id,
    source.account_number AS source_account,
    ar.target_account_id,
    target.account_number AS target_account,
    ar.relationship_type,
    ar.confidence_score,
    ar.detected_at
FROM account_relationship ar
JOIN account source
    ON source.account_id = ar.source_account_id
JOIN account target
    ON target.account_id = ar.target_account_id
WHERE ar.relationship_type IN (
    'DIRECT_TRANSFER',
    'COMMON_BENEFICIARY'
)
ORDER BY
    ar.confidence_score DESC;

/*
=========================================================
8. INVESTIGATION FEATURE SCORING
=========================================================
*/


-- 8.1 Calculate basic behavioral features for each account
-- These features can be used by the fraud-risk engine.

WITH account_features AS (
    SELECT
        a.account_id,
        a.account_number,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
        ) AS transaction_count,

        COALESCE(
            SUM(t.amount) FILTER (
                WHERE t.status = 'SUCCESS'
            ),
            0
        ) AS total_transaction_amount,

        COALESCE(
            AVG(t.amount) FILTER (
                WHERE t.status = 'SUCCESS'
            ),
            0
        ) AS average_transaction_amount,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
              AND t.amount >= 50000
        ) AS high_value_transaction_count

    FROM account a
    LEFT JOIN transaction t
        ON t.sender_account_id = a.account_id
    GROUP BY
        a.account_id,
        a.account_number
)
SELECT
    account_id,
    account_number,
    transaction_count,
    total_transaction_amount,
    average_transaction_amount,
    high_value_transaction_count
FROM account_features
ORDER BY
    total_transaction_amount DESC;


-- 8.2 Calculate rapid transaction behavior
-- Counts transactions that occur within 10 minutes
-- of the previous transaction from the same account.

WITH transaction_timing AS (
    SELECT
        t.sender_account_id AS account_id,
        t.transaction_id,
        t.txn_time,

        LAG(t.txn_time) OVER (
            PARTITION BY t.sender_account_id
            ORDER BY t.txn_time
        ) AS previous_txn_time

    FROM transaction t
    WHERE t.status = 'SUCCESS'
),
rapid_activity AS (
    SELECT
        account_id,
        COUNT(*) AS rapid_transaction_count
    FROM transaction_timing
    WHERE previous_txn_time IS NOT NULL
      AND txn_time - previous_txn_time
          <= INTERVAL '10 minutes'
    GROUP BY account_id
)
SELECT
    a.account_id,
    a.account_number,
    COALESCE(
        ra.rapid_transaction_count,
        0
    ) AS rapid_transaction_count
FROM account a
LEFT JOIN rapid_activity ra
    ON ra.account_id = a.account_id
ORDER BY
    rapid_transaction_count DESC;


-- 8.3 Combine behavioral indicators
-- Creates an investigation feature table in query form.

WITH transaction_features AS (
    SELECT
        a.account_id,
        a.account_number,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
        ) AS transaction_count,

        COALESCE(
            SUM(t.amount) FILTER (
                WHERE t.status = 'SUCCESS'
            ),
            0
        ) AS total_transaction_amount,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
              AND t.amount >= 50000
        ) AS high_value_transaction_count

    FROM account a
    LEFT JOIN transaction t
        ON t.sender_account_id = a.account_id
    GROUP BY
        a.account_id,
        a.account_number
),
rapid_features AS (
    SELECT
        account_id,
        COUNT(*) AS rapid_transaction_count
    FROM (
        SELECT
            t.sender_account_id AS account_id,
            t.txn_time,
            LAG(t.txn_time) OVER (
                PARTITION BY t.sender_account_id
                ORDER BY t.txn_time
            ) AS previous_txn_time
        FROM transaction t
        WHERE t.status = 'SUCCESS'
    ) timing
    WHERE previous_txn_time IS NOT NULL
      AND txn_time - previous_txn_time
          <= INTERVAL '10 minutes'
    GROUP BY account_id
),
risk_features AS (
    SELECT
        account_id,
        MAX(risk_score) AS maximum_risk_score,
        AVG(risk_score) AS average_risk_score
    FROM risk_assessment
    GROUP BY account_id
)
SELECT
    tf.account_id,
    tf.account_number,

    tf.transaction_count,
    tf.total_transaction_amount,
    tf.high_value_transaction_count,

    COALESCE(
        rf.rapid_transaction_count,
        0
    ) AS rapid_transaction_count,

    COALESCE(
        rs.maximum_risk_score,
        0
    ) AS maximum_risk_score,

    COALESCE(
        rs.average_risk_score,
        0
    ) AS average_risk_score

FROM transaction_features tf

LEFT JOIN rapid_features rf
    ON rf.account_id = tf.account_id

LEFT JOIN risk_features rs
    ON rs.account_id = tf.account_id

ORDER BY
    maximum_risk_score DESC,
    rapid_transaction_count DESC,
    total_transaction_amount DESC;


-- 8.4 Generate an investigation indicator score
-- This is a rule-based analytical score, NOT a final
-- fraud decision or ML prediction.

WITH transaction_features AS (
    SELECT
        a.account_id,
        a.account_number,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
        ) AS transaction_count,

        COALESCE(
            SUM(t.amount) FILTER (
                WHERE t.status = 'SUCCESS'
            ),
            0
        ) AS total_amount,

        COUNT(t.transaction_id) FILTER (
            WHERE t.status = 'SUCCESS'
              AND t.amount >= 50000
        ) AS high_value_count

    FROM account a
    LEFT JOIN transaction t
        ON t.sender_account_id = a.account_id

    GROUP BY
        a.account_id,
        a.account_number
),

risk_features AS (
    SELECT
        account_id,
        MAX(risk_score) AS maximum_risk_score
    FROM risk_assessment
    GROUP BY account_id
)

SELECT
    tf.account_id,
    tf.account_number,
    tf.transaction_count,
    tf.total_amount,
    tf.high_value_count,

    COALESCE(
        rf.maximum_risk_score,
        0
    ) AS maximum_risk_score,

    (
        CASE
            WHEN tf.transaction_count >= 3
                THEN 20
            ELSE 0
        END

        +

        CASE
            WHEN tf.total_amount >= 100000
                THEN 20
            ELSE 0
        END

        +

        CASE
            WHEN tf.high_value_count >= 1
                THEN 20
            ELSE 0
        END

        +

        CASE
            WHEN COALESCE(rf.maximum_risk_score, 0) >= 80
                THEN 40
            ELSE 0
        END
    ) AS investigation_indicator_score

FROM transaction_features tf

LEFT JOIN risk_features rf
    ON rf.account_id = tf.account_id

ORDER BY
    investigation_indicator_score DESC,
    maximum_risk_score DESC;