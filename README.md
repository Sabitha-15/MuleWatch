# MuleWatch

## AI-Powered Mule Account Detection & Financial Fraud Investigation System

MuleWatch is a database-centric fraud investigation platform designed to identify potentially suspicious mule-account behaviour, automatically generate fraud alerts, and provide investigators with tools for transaction analysis, connected-account investigation and money-flow tracing.

## Architecture

```text
React
   |
   v
FastAPI
   |
   v
PostgreSQL
   |
   +---- ML Risk Engine
   |
   +---- Fraud Alerts
   |
   +---- Fraud Cases
   |
   +---- Investigation History
   |
   +---- Account Network
   |
   +---- Money Flow
```

## Core Features

- Transaction ingestion
- Idempotent transaction processing
- Account and transaction management
- Account-level ML risk scoring
- Automatic fraud-alert generation
- Fraud case management
- Investigator notes
- Investigation findings
- Case lifecycle and audit history
- Transaction investigation timeline
- Connected-account network analysis
- Recursive money-flow tracing
- Risk evidence analysis
- Investigation dashboard
- PostgreSQL views and indexes
- PL/pgSQL functions
- PL/pgSQL procedures
- Database triggers
- Cursor-based periodic review
- Phase 2 customer management with audit history
- Advanced transaction explorer with status-transition auditing
- Recursive interactive account network graph
- Immutable investigation report snapshots

## Machine Learning

The ML pipeline extracts behavioural features including:

- transaction frequency
- incoming/outgoing volume
- rapid transfers
- unique counterparties
- amount variability
- behavioural deviation
- transaction velocity
- money-flow relationships

The production model is a Gradient Boosting classifier trained on synthetic/anonymized mule-account behaviour.

The model is used as a decision-support mechanism. A risk score does not represent a declaration of guilt.

## Database

PostgreSQL is the primary DBMS.

The relational design follows 3NF and contains entities including:

- CUSTOMER
- ACCOUNT
- BENEFICIARY
- TRANSACTION
- RISK_ASSESSMENT
- FRAUD_ALERT
- INVESTIGATOR
- FRAUD_CASE
- CASE_TRANSACTION
- CASE_NOTE
- CASE_STATUS_HISTORY
- ACCOUNT_RELATIONSHIP

## Investigation Workflow

```text
Transaction
→ Behaviour Analysis
→ ML Risk Assessment
→ Fraud Alert
→ Investigator Review
→ Fraud Case
→ Transaction Timeline
→ Account Network
→ Money Flow
→ Evidence
→ Investigator Finding
→ Case Decision
```

## Technology Stack

### Frontend
- React
- Vite
- Axios
- Recharts
- Lucide React

### Backend
- Python
- FastAPI
- psycopg

### Database
- PostgreSQL

### Machine Learning
- Python
- pandas
- NumPy
- scikit-learn
- joblib

### Development
- Git
- GitHub
- VS Code

## Project Structure

```text
MuleWatch/
├── backend/
├── database/
├── docs/
├── frontend/
├── ml/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Database Layer

The database layer contains:

- normalized relational schema
- primary and foreign keys
- integrity constraints
- advanced joins and aggregations
- subqueries and correlated queries
- CTEs and recursive queries
- window functions
- analytical views
- performance indexes
- PL/pgSQL functions
- stored procedures
- triggers
- transaction validation
- fraud-alert automation
- case-status auditing
- account-relationship maintenance
- cursor-based periodic risk review

## Risk and Alert Pipeline

```text
New Transaction
      |
      v
Transaction Validation
      |
      v
ML Behaviour Analysis
      |
      v
Risk Assessment
      |
      v
Risk Threshold Check
      |
      v
Fraud Alert
      |
      v
Investigator Review
```

Risk assessments are stored in PostgreSQL and can automatically generate fraud alerts when configured thresholds are crossed.

## Investigation Workflow

Investigators can:

- review fraud alerts
- inspect account information
- review linked transactions
- add investigation notes
- inspect case status history
- trace connected accounts
- analyse money movement
- record investigation findings
- close cases with a documented reason

## Responsible Use

MuleWatch is an academic and engineering prototype using simulated/anonymized data.

ML risk scores are investigation indicators and decision-support signals. They do not establish that an account holder has committed fraud.

## Future Extensions

Potential future extensions include:

- streaming transaction ingestion
- real-time event processing
- graph database integration
- advanced graph-based mule detection
- model monitoring and drift detection
- explainable AI dashboards
- role-based access control
- cloud deployment
- database partitioning for large transaction volumes
- distributed processing for large-scale investigations


## Phase 2 Evaluation Features

Run `database/10_phase2_customer_management.sql` (if not already applied), followed by `database/11_phase2_advanced_features.sql`. The optional rollback-safe demonstration script is `database/12_phase2_tests.sql`. See `docs/PHASE2_DBMS_NORMALIZATION.md` for the 1NF/2NF/3NF explanation and DBMS object mapping.

The Phase 2 GUI adds Transaction Explorer, Account Network and Investigation Reports. Customer Management is available from the Accounts page. The new backend endpoints are grouped under `/api/phase2`.
