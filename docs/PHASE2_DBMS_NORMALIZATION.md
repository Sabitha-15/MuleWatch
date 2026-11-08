# MuleWatch — Phase 2 DBMS Design and Normalization Notes

## Phase 2 feature mapping

1. **Customer Management (completed):** `customer_audit_log`, `trg_phase2_customer_audit`, `sp_phase2_update_customer_status`, and `fn_phase2_customer_summary` support customer status management, audit history, and a customer-level summary.
2. **Advanced Transaction Explorer:** `vw_phase2_transaction_explorer` provides a reusable joined transaction view. `sp_phase2_update_transaction_status` finalizes pending transactions, while `trg_phase2_transaction_status_audit` records status changes in `transaction_status_audit`.
3. **Interactive Account Network Graph:** `fn_phase2_account_network` uses a recursive CTE to traverse account relationships, tracks the path to avoid cycles, and limits traversal depth.
4. **Investigation Report Generation:** `sp_phase2_generate_case_report` stores a JSONB snapshot of a case and its linked evidence. `fn_phase2_get_case_report` retrieves a snapshot. A trigger prevents modification or deletion of generated snapshots.

## Normalization explanation

The core relational schema is designed around separate entities: CUSTOMER, ACCOUNT, BENEFICIARY, TRANSACTION, RISK_ASSESSMENT, FRAUD_ALERT, INVESTIGATOR, FRAUD_CASE, CASE_TRANSACTION, CASE_NOTE, CASE_STATUS_HISTORY, and ACCOUNT_RELATIONSHIP.

### First Normal Form (1NF)
- Each table has a primary key.
- Attributes store single values rather than repeating lists or arrays of transaction/customer details.
- Repeating transaction, note, status-history, and relationship records are represented as separate rows.

### Second Normal Form (2NF)
- Tables with a single-column primary key have no partial dependency on part of a key.
- `CASE_TRANSACTION` uses the composite key `(case_id, transaction_id)`. Its non-key attributes (`linked_at`, `link_reason`) describe the complete case–transaction association, not only one side of the key.

### Third Normal Form (3NF)
- Customer details are stored in CUSTOMER rather than copied into ACCOUNT or TRANSACTION.
- Account details are stored in ACCOUNT; transaction facts reference sender and receiver account IDs.
- Investigator details are stored in INVESTIGATOR; notes and case history reference investigator IDs.
- Case notes and status transitions are stored separately rather than as repeating columns in FRAUD_CASE.
- This separation reduces update, insertion, and deletion anomalies.

### Why the associative table exists
`CASE_TRANSACTION` resolves the many-to-many relationship between FRAUD_CASE and TRANSACTION. Its composite primary key prevents the same transaction from being linked twice to the same case.

### Important distinction
The normalization explanation describes the intended relational design and key dependencies. The Phase 2 additions are audit/reporting tables and views; they do not denormalize the existing core tables. JSONB in `case_investigation_report` is a historical report snapshot, not a replacement for the normalized operational tables.

## Phase 2 objects to demonstrate in pgAdmin

| Concept | Object | Demonstration |
|---|---|---|
| View | `vw_phase2_transaction_explorer` | Query joined transaction, account, customer and latest risk information |
| Trigger | `trg_phase2_transaction_status_audit` | Finalize a PENDING transaction and inspect `transaction_status_audit` |
| Procedure | `sp_phase2_update_transaction_status` | Apply a validated PENDING → SUCCESS/FAILED transition |
| Recursive function | `fn_phase2_account_network` | Query connected accounts at depth 1–5 |
| Procedure | `sp_phase2_generate_case_report` | Generate and persist a case report snapshot |
| Function | `fn_phase2_get_case_report` | Retrieve a saved report snapshot |
| Trigger | `trg_phase2_immutable_case_report` | Demonstrate that a saved report cannot be edited/deleted |

## Migration order

Run the existing schema and existing migrations first, including `10_phase2_customer_management.sql`. Then run `11_phase2_advanced_features.sql` once in the `mulewatch` database. The migration is written to be safely re-runnable.
