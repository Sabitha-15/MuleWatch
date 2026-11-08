# Phase 2 Change Log

## Already completed before this update

- Customer Management GUI on the Accounts page.
- `customer_audit_log` table and `trg_phase2_customer_audit` trigger.
- `sp_phase2_update_customer_status` stored procedure.
- `fn_phase2_customer_summary` customer summary function.
- Customer status update and audit history were manually verified in pgAdmin and the GUI in the user's environment.

## Added in this update

- Advanced Transaction Explorer page and parameterized API filters.
- Transaction explorer SQL view and supporting indexes.
- Transaction status finalization procedure, audit table and audit trigger.
- Recursive account network function, API endpoint and clickable SVG graph page.
- Investigation report snapshot table, report-generation procedure, retrieval function and immutable-report trigger.
- Investigation Reports page with report history and print/save-to-PDF action.
- Phase 2 SQL test script and 1NF/2NF/3NF explanation.

## Validation performed on the package

- Python syntax compilation passed for the new Phase 2 router and updated FastAPI entry point.
- The frontend production build could not be run in this environment because npm dependencies were not available from the package registry/cache. Run `npm install` and `npm run build` locally after extracting the ZIP.
- PostgreSQL migration execution must be performed against the user's `mulewatch` database; no live database connection was available during package preparation.
