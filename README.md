# c1-navigators-project-3
# AI Credit-Risk Investigation Agent Backend

PostgreSQL-backed FastAPI integration layer for the Banking AI Credit-Risk Investigation Agent.

## Responsibilities

- Credit application intake
- Case management
- Investigation lifecycle
- PostgreSQL persistence
- AI component contracts
- Evidence synthesis
- Report persistence/retrieval

## PostgreSQL setup

1. Install PostgreSQL.
2. Create the database:

```sql
CREATE DATABASE credit_risk_db;
```

3. Copy `.env.example` to `.env`.
4. Replace `YOUR_PASSWORD` in `DATABASE_URL` with your PostgreSQL password.

Example:

```text
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/credit_risk_db
```

## Install

```bash
python -m venv myenv
myenv\Scripts\activate
pip install -r requirements.txt
```

## Create tables

```bash
python -m app.db.init_db
```

## Run

```bash
python -m uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## API workflow

```text
POST /applications
        ↓
POST /cases
        ↓
POST /investigations/{case_id}/run
        ↓
AI integration interfaces
        ↓
Evidence synthesis
        ↓
PostgreSQL report
        ↓
GET /reports/{case_id}
```

## PostgreSQL tables

- `applications` — applicant/application data, financial JSON and transactions JSON
- `cases` — investigation case and analyst assignment
- `investigations` — execution/status history
- `reports` — generated investigation reports

Financial data and transactions intentionally use PostgreSQL JSON columns in this first version. They can be normalized later if the PRD requires detailed transaction querying.

## AI integration interfaces

The real AI implementations should replace the mock classes in `app/integrations/`:

- `policy_rag.py`
- `financial_analysis.py`
- `transaction_analysis.py`
- `anomaly_detection.py`
- `credit_risk_model.py`
- `report_generator.py`

The FastAPI contracts can remain stable while the underlying AI implementations change.

## Production note

The project includes Alembic as a dependency. This prototype creates tables with SQLAlchemy's `create_all()` to keep initial setup simple. Before deployment, initialize Alembic and use migrations for schema changes.
