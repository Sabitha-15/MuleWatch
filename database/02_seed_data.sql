-- ============================================================
-- MuleWatch
-- 02_seed_data.sql
-- Simulated/anonymized seed data
-- ============================================================

INSERT INTO customer
    (full_name, email, phone, date_of_birth, status)
VALUES
    ('Rahul Kumar', 'rahul.kumar@example.com', '+919800000001',
     '1998-04-12', 'ACTIVE'),

    ('Ananya Sharma', 'ananya.sharma@example.com', '+919800000002',
     '1997-08-21', 'ACTIVE'),

    ('Vikram Reddy', 'vikram.reddy@example.com', '+919800000003',
     '1995-02-10', 'ACTIVE'),

    ('Priya Nair', 'priya.nair@example.com', '+919800000004',
     '1999-11-05', 'ACTIVE'),

    ('Arjun Mehta', 'arjun.mehta@example.com', '+919800000005',
     '1996-06-18', 'ACTIVE');

     -- ============================================================
-- ACCOUNTS
-- ============================================================

INSERT INTO account
    (customer_id, account_number, account_type, balance, status)
VALUES
    (1, 'MWACC100001', 'SAVINGS', 125000.00, 'ACTIVE'),
    (1, 'MWACC100002', 'CURRENT', 85000.00, 'ACTIVE'),

    (2, 'MWACC100003', 'SAVINGS', 210000.00, 'ACTIVE'),
    (2, 'MWACC100004', 'CURRENT', 45000.00, 'ACTIVE'),

    (3, 'MWACC100005', 'SAVINGS', 175000.00, 'ACTIVE'),
    (3, 'MWACC100006', 'CURRENT', 92000.00, 'ACTIVE'),

    (4, 'MWACC100007', 'SAVINGS', 320000.00, 'ACTIVE'),
    (4, 'MWACC100008', 'CURRENT', 65000.00, 'ACTIVE'),

    (5, 'MWACC100009', 'SAVINGS', 95000.00, 'ACTIVE'),
    (5, 'MWACC100010', 'CURRENT', 55000.00, 'ACTIVE');

    -- ============================================================
-- BENEFICIARIES
-- ============================================================

INSERT INTO beneficiary
    (account_id, beneficiary_name, beneficiary_account_number, bank_name, status)
VALUES
    (1, 'Apex Traders', 'BEN001001', 'MuleBank', 'ACTIVE'),
    (2, 'Nova Services', 'BEN001002', 'MuleBank', 'ACTIVE'),
    (3, 'Apex Traders', 'BEN001001', 'MuleBank', 'ACTIVE'),
    (4, 'Vertex Solutions', 'BEN001004', 'MuleBank', 'ACTIVE'),
    (5, 'Nova Services', 'BEN001002', 'MuleBank', 'ACTIVE'),
    (6, 'Rapid Logistics', 'BEN001006', 'MuleBank', 'ACTIVE'),
    (7, 'Apex Traders', 'BEN001001', 'MuleBank', 'ACTIVE'),
    (8, 'Global Supplies', 'BEN001008', 'MuleBank', 'ACTIVE'),
    (9, 'Rapid Logistics', 'BEN001006', 'MuleBank', 'ACTIVE'),
    (10, 'Global Supplies', 'BEN001008', 'MuleBank', 'ACTIVE');
 -- ============================================================
-- INVESTIGATORS
-- ============================================================

INSERT INTO investigator
    (full_name, email, department, role, status)
VALUES
    ('Meera Rao', 'meera.rao@mulewatch.local',
     'Financial Crime', 'Senior Investigator', 'ACTIVE'),

    ('Karan Singh', 'karan.singh@mulewatch.local',
     'Financial Crime', 'Fraud Analyst', 'ACTIVE'),

    ('Neha Iyer', 'neha.iyer@mulewatch.local',
     'Risk Intelligence', 'Risk Investigator', 'ACTIVE');
   
INSERT INTO transaction
    (sender_account_id, receiver_account_id, beneficiary_id, amount, txn_time, transaction_type, channel, status, description)
VALUES
-- Normal transactions
(1, 3, 1, 5000.00, '2026-09-01 10:15:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Regular transfer'),
(3, 5, 3, 7500.00, '2026-09-02 11:30:00', 'TRANSFER', 'NETBANKING', 'SUCCESS', 'Regular transfer'),
(7, 9, 7, 12000.00, '2026-09-03 14:20:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Regular transfer'),

-- Suspicious rapid movement
(1, 5, 1, 85000.00, '2026-09-10 09:00:00', 'TRANSFER', 'UPI', 'SUCCESS', 'High value transfer'),
(5, 7, 3, 82000.00, '2026-09-10 09:08:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Rapid onward transfer'),
(7, 9, 7, 79000.00, '2026-09-10 09:17:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Rapid onward transfer'),

-- Another suspicious chain
(2, 6, 2, 45000.00, '2026-09-11 15:00:00', 'TRANSFER', 'NETBANKING', 'SUCCESS', 'Large transfer'),
(6, 8, 6, 43000.00, '2026-09-11 15:07:00', 'TRANSFER', 'NETBANKING', 'SUCCESS', 'Rapid movement'),
(8, 10, 8, 41000.00, '2026-09-11 15:15:00', 'TRANSFER', 'NETBANKING', 'SUCCESS', 'Rapid movement'),

-- Multiple transactions to same beneficiary
(9, 3, 9, 25000.00, '2026-09-12 10:00:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Repeated beneficiary transfer'),
(9, 5, 9, 28000.00, '2026-09-12 10:20:00', 'TRANSFER', 'UPI', 'SUCCESS', 'Repeated beneficiary transfer'),

-- Failed/pending examples
(4, 2, 4, 15000.00, '2026-09-13 12:00:00', 'TRANSFER', 'UPI', 'FAILED', 'Transaction failed'),
(10, 1, 10, 9000.00, '2026-09-13 13:00:00', 'TRANSFER', 'MOBILE', 'PENDING', 'Transaction pending');

INSERT INTO risk_assessment
    (account_id, transaction_id, risk_score, risk_level, model_version, reason)
VALUES
(1, 1, 18.00, 'LOW', 'v1.0', 'Normal transaction pattern'),
(3, 2, 22.00, 'LOW', 'v1.0', 'Normal transaction pattern'),
(7, 3, 25.00, 'LOW', 'v1.0', 'Normal transaction pattern'),

(1, 4, 91.00, 'CRITICAL', 'v1.0',
 'High-value transfer followed by rapid onward movement'),

(5, 5, 94.00, 'CRITICAL', 'v1.0',
 'Rapid transfer shortly after receiving high-value funds'),

(7, 6, 89.00, 'HIGH', 'v1.0',
 'Rapid onward transfer indicating possible fund layering'),

(2, 7, 72.00, 'MEDIUM', 'v1.0',
 'Large-value transaction requiring additional review'),

(6, 8, 88.00, 'HIGH', 'v1.0',
 'Rapid movement of funds after receiving transfer'),

(8, 9, 93.00, 'CRITICAL', 'v1.0',
 'Rapid onward movement of high-value funds'),

(9, 10, 76.00, 'MEDIUM', 'v1.0',
 'Repeated transfers involving the same beneficiary'),

(9, 11, 82.00, 'HIGH', 'v1.0',
 'Repeated high-value transfers to related beneficiary'),

(4, 12, 10.00, 'LOW', 'v1.0',
 'Failed transaction'),

(10, 13, 35.00, 'LOW', 'v1.0',
 'Pending transaction with no immediate suspicious indicators');