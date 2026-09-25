-- ============================================================
-- MuleWatch
-- 01_schema.sql
-- Complete relational database schema
-- PostgreSQL
-- ============================================================


-- ============================================================
-- 1. CUSTOMER
-- ============================================================

CREATE TABLE customer (
    customer_id BIGSERIAL PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(150) UNIQUE,

    phone VARCHAR(20) UNIQUE,

    date_of_birth DATE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT chk_customer_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED'))
);


-- ============================================================
-- 2. ACCOUNT
-- ============================================================

CREATE TABLE account (
    account_id BIGSERIAL PRIMARY KEY,

    customer_id BIGINT NOT NULL,

    account_number VARCHAR(30) NOT NULL UNIQUE,

    account_type VARCHAR(20) NOT NULL,

    balance NUMERIC(15,2) NOT NULL DEFAULT 0,

    opened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id),

    CONSTRAINT chk_account_type
        CHECK (account_type IN ('SAVINGS', 'CURRENT')),

    CONSTRAINT chk_account_balance
        CHECK (balance >= 0),

    CONSTRAINT chk_account_status
        CHECK (status IN ('ACTIVE', 'BLOCKED', 'CLOSED'))
);


-- ============================================================
-- 3. BENEFICIARY
-- ============================================================

CREATE TABLE beneficiary (
    beneficiary_id BIGSERIAL PRIMARY KEY,

    account_id BIGINT NOT NULL,

    beneficiary_name VARCHAR(100) NOT NULL,

    beneficiary_account_number VARCHAR(30) NOT NULL,

    bank_name VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT fk_beneficiary_account
        FOREIGN KEY (account_id)
        REFERENCES account(account_id),

    CONSTRAINT chk_beneficiary_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED'))
);


-- ============================================================
-- 4. TRANSACTION
-- ============================================================

CREATE TABLE transaction (
    transaction_id BIGSERIAL PRIMARY KEY,

    sender_account_id BIGINT NOT NULL,

    receiver_account_id BIGINT NOT NULL,

    beneficiary_id BIGINT,

    amount NUMERIC(15,2) NOT NULL,

    txn_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    transaction_type VARCHAR(30) NOT NULL,

    channel VARCHAR(30),

    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',

    description TEXT,

    CONSTRAINT fk_transaction_sender
        FOREIGN KEY (sender_account_id)
        REFERENCES account(account_id),

    CONSTRAINT fk_transaction_receiver
        FOREIGN KEY (receiver_account_id)
        REFERENCES account(account_id),

    CONSTRAINT fk_transaction_beneficiary
        FOREIGN KEY (beneficiary_id)
        REFERENCES beneficiary(beneficiary_id),

    CONSTRAINT chk_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT chk_transaction_sender_receiver
        CHECK (sender_account_id <> receiver_account_id),

    CONSTRAINT chk_transaction_status
        CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING')),

    CONSTRAINT chk_transaction_type
        CHECK (
            transaction_type IN (
                'TRANSFER',
                'DEPOSIT',
                'WITHDRAWAL'
            )
        )
);


-- ============================================================
-- 5. RISK ASSESSMENT
-- ============================================================

CREATE TABLE risk_assessment (
    risk_assessment_id BIGSERIAL PRIMARY KEY,

    account_id BIGINT NOT NULL,

    transaction_id BIGINT,

    risk_score NUMERIC(5,2) NOT NULL,

    risk_level VARCHAR(20) NOT NULL,

    model_version VARCHAR(30) NOT NULL,

    assessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    reason TEXT,

    CONSTRAINT fk_risk_account
        FOREIGN KEY (account_id)
        REFERENCES account(account_id),

    CONSTRAINT fk_risk_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transaction(transaction_id),

    CONSTRAINT chk_risk_score
        CHECK (risk_score >= 0 AND risk_score <= 100),

    CONSTRAINT chk_risk_level
        CHECK (
            risk_level IN (
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL'
            )
        )
);


-- ============================================================
-- 6. FRAUD ALERT
-- ============================================================

CREATE TABLE fraud_alert (
    alert_id BIGSERIAL PRIMARY KEY,

    risk_assessment_id BIGINT NOT NULL,

    account_id BIGINT NOT NULL,

    alert_level VARCHAR(20) NOT NULL,

    alert_status VARCHAR(20) NOT NULL DEFAULT 'OPEN',

    alert_message TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    resolved_at TIMESTAMP,

    CONSTRAINT fk_alert_risk_assessment
        FOREIGN KEY (risk_assessment_id)
        REFERENCES risk_assessment(risk_assessment_id),

    CONSTRAINT fk_alert_account
        FOREIGN KEY (account_id)
        REFERENCES account(account_id),

    CONSTRAINT chk_alert_level
        CHECK (
            alert_level IN (
                'HIGH',
                'CRITICAL'
            )
        ),

    CONSTRAINT chk_alert_status
        CHECK (
            alert_status IN (
                'OPEN',
                'UNDER_REVIEW',
                'RESOLVED',
                'DISMISSED'
            )
        ),

    CONSTRAINT chk_alert_resolution_time
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= created_at
        )
);


-- ============================================================
-- 7. INVESTIGATOR
-- ============================================================

CREATE TABLE investigator (
    investigator_id BIGSERIAL PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    department VARCHAR(100),

    role VARCHAR(50) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_investigator_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE'
            )
        )
);


-- ============================================================
-- 8. FRAUD CASE
-- ============================================================

CREATE TABLE fraud_case (
    case_id BIGSERIAL PRIMARY KEY,

    alert_id BIGINT,

    account_id BIGINT NOT NULL,

    investigator_id BIGINT,

    case_title VARCHAR(200) NOT NULL,

    case_description TEXT,

    case_status VARCHAR(30) NOT NULL DEFAULT 'OPEN',

    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',

    opened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    closed_at TIMESTAMP,

    CONSTRAINT fk_case_alert
        FOREIGN KEY (alert_id)
        REFERENCES fraud_alert(alert_id),

    CONSTRAINT fk_case_account
        FOREIGN KEY (account_id)
        REFERENCES account(account_id),

    CONSTRAINT fk_case_investigator
        FOREIGN KEY (investigator_id)
        REFERENCES investigator(investigator_id),

    CONSTRAINT chk_case_status
        CHECK (
            case_status IN (
                'OPEN',
                'UNDER_REVIEW',
                'ESCALATED',
                'CLOSED'
            )
        ),

    CONSTRAINT chk_case_priority
        CHECK (
            priority IN (
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL'
            )
        ),

    CONSTRAINT chk_case_closure_time
        CHECK (
            closed_at IS NULL
            OR closed_at >= opened_at
        )
);


-- ============================================================
-- 9. CASE TRANSACTION
-- ============================================================

CREATE TABLE case_transaction (
    case_id BIGINT NOT NULL,

    transaction_id BIGINT NOT NULL,

    linked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    link_reason TEXT,

    CONSTRAINT pk_case_transaction
        PRIMARY KEY (case_id, transaction_id),

    CONSTRAINT fk_case_transaction_case
        FOREIGN KEY (case_id)
        REFERENCES fraud_case(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_transaction_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transaction(transaction_id)
);


-- ============================================================
-- 10. CASE NOTE
-- ============================================================

CREATE TABLE case_note (
    note_id BIGSERIAL PRIMARY KEY,

    case_id BIGINT NOT NULL,

    investigator_id BIGINT,

    note_text TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_case_note_case
        FOREIGN KEY (case_id)
        REFERENCES fraud_case(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_note_investigator
        FOREIGN KEY (investigator_id)
        REFERENCES investigator(investigator_id)
);


-- ============================================================
-- 11. CASE STATUS HISTORY
-- ============================================================

CREATE TABLE case_status_history (
    history_id BIGSERIAL PRIMARY KEY,

    case_id BIGINT NOT NULL,

    old_status VARCHAR(30),

    new_status VARCHAR(30) NOT NULL,

    changed_by BIGINT,

    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    change_reason TEXT,

    CONSTRAINT fk_status_history_case
        FOREIGN KEY (case_id)
        REFERENCES fraud_case(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_status_history_investigator
        FOREIGN KEY (changed_by)
        REFERENCES investigator(investigator_id),

    CONSTRAINT chk_status_history_new_status
        CHECK (
            new_status IN (
                'OPEN',
                'UNDER_REVIEW',
                'ESCALATED',
                'CLOSED'
            )
        ),

    CONSTRAINT chk_status_history_old_status
        CHECK (
            old_status IS NULL
            OR old_status IN (
                'OPEN',
                'UNDER_REVIEW',
                'ESCALATED',
                'CLOSED'
            )
        )
);


-- ============================================================
-- 12. ACCOUNT RELATIONSHIP
-- ============================================================

CREATE TABLE account_relationship (
    relationship_id BIGSERIAL PRIMARY KEY,

    source_account_id BIGINT NOT NULL,

    target_account_id BIGINT NOT NULL,

    relationship_type VARCHAR(30) NOT NULL,

    confidence_score NUMERIC(5,2),

    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    notes TEXT,

    CONSTRAINT fk_relationship_source
        FOREIGN KEY (source_account_id)
        REFERENCES account(account_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_relationship_target
        FOREIGN KEY (target_account_id)
        REFERENCES account(account_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_relationship_different_accounts
        CHECK (
            source_account_id <> target_account_id
        ),

    CONSTRAINT chk_relationship_confidence
        CHECK (
            confidence_score IS NULL
            OR (
                confidence_score >= 0
                AND confidence_score <= 100
            )
        ),

    CONSTRAINT chk_relationship_type
        CHECK (
            relationship_type IN (
                'DIRECT_TRANSFER',
                'COMMON_BENEFICIARY',
                'SHARED_DEVICE',
                'SHARED_IP',
                'NETWORK_LINK'
            )
        )
);