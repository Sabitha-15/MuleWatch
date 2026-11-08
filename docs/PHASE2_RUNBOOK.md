# MuleWatch Phase 2 — Apply and Run

## 1. Database migration

Open pgAdmin Query Tool and select the **mulewatch** database (not `postgres`). Confirm the database selector at the top says `mulewatch`.

Run these only if they have not already been applied:

1. `database/10_phase2_customer_management.sql` — Customer Management (already completed in the current project, so do not rerun just for testing unless needed).
2. `database/11_phase2_advanced_features.sql` — adds Transaction Explorer, recursive Account Network, transaction status auditing and report snapshots.

Then run `database/12_phase2_tests.sql`. Its data-changing tests are wrapped in transactions and rolled back.

## 2. Start the backend

From the MuleWatch project root in Command Prompt:

```cmd
.venv\Scripts\activate
uvicorn backend.main:app --reload
```

The API should be available at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/docs` and confirm the **Phase 2** endpoints appear.

## 3. Start the frontend

Open a second terminal:

```cmd
cd frontend
npm install
npm run dev
```

Open the local Vite URL, normally `http://localhost:5173`.

## 4. Phase 2 GUI

- **Customer Management:** Accounts page → Customer Management.
- **Transaction Explorer:** sidebar → Transaction Explorer. Search/filter records. Only PENDING rows can be finalized; enter a reason when prompted. The database trigger writes the audit row.
- **Account Network:** sidebar → Account Network. Enter a root account ID and depth 1–5. Click a node to make it the new root.
- **Investigation Reports:** sidebar → Investigation Reports. Enter an existing case ID, optionally an active investigator ID, and generate a snapshot. Use Print / Save PDF for a printable copy.

## 5. Important behaviour

- Transaction status changes are restricted to PENDING → SUCCESS or PENDING → FAILED by the stored procedure.
- Transaction status changes are recorded by a database trigger in `transaction_status_audit`.
- Network traversal uses the stored `account_relationship` records. If the graph is empty, run the existing `CALL sp_refresh_account_relationships();` after reviewing its effects, then reload the graph.
- Report snapshots are immutable. If case data changes, generate a new report rather than editing an existing snapshot.
- The project uses simulated/anonymized data. Risk scores are investigation indicators, not proof of fraud.

## 6. Security and archive hygiene

Do not share `.env`, database passwords, `.venv`, `node_modules`, or `.git` in project archives. Keep your local `.env` file in the project root; it is intentionally not included in this Phase 2 package. If credentials were included in a shared archive, rotate the database password.
