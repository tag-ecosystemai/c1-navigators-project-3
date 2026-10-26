# c1-navigators-project-3

Demo guide
Fresh clone on Windows (Git Bash)
git clone <repo-url> && cd <repo-folder>
git checkout feat/azure-demo            # or main once merged
python -m venv .venv
source .venv/Scripts/activate
pip install -r ai_engineering/requirements.txt
cp .env.example .env                    # then fill in the Azure values: docs/AZURE_SETUP.md
python -m ai_engineering.rag.cli doctor # must end with "All checks passed."
python -m pytest ai_engineering/tests -q
Without Azure values you can still run everything except the Azure parts: use --offline.

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


# Credence — Credit Risk Investigation Agent Frontend

Decision-support workstation for credit analysts and risk supervisors to investigate loan applications, inspect multi-agent orchestration steps, evaluate 14 underwriting policies, review ML default probabilities, and cross-check findings with Azure OpenAI RAG citations.

---

## 🚀 Key Features

* **5 Golden Personas (`1`–`5`)**: Instant switching between Prime, Income Discrepancy, Gambling/NSF, Undisclosed Debt, and Knockout bankruptcy test cases.
* **4-Agent Pipeline Visualization**: Real-time tracking of Data Analysis, Compliance, Credit Risk, and Explanation agents with millisecond execution latencies.
* **Verdict Hero & Primary Driver**: Prominently highlights the rule driver (e.g. 57.3% income variance or $740 hidden debt) and reinforces *"Human Analyst Makes Final Decision"*.
* **14-Rule Policy Matrix**: Interactive breakdown of all 14 evaluated rules with category filters, quantitative range visualizers, policy citations, and verbatim policy document excerpts.
* **ML Probability of Default ($PD$)**: Radial gauge and top feature attribution bars (e.g. Income Stability, Gambling Spend, DTI) explaining risk drivers.
* **Policy RAG Cross-Check**: Real-time comparison drawer showing agreement between the rule evaluator and Azure OpenAI RAG.
* **Side-by-Side Comparison Matrix (`C`)**: Comparative view across all 5 personas.
* **Credit Investigation Memorandum (`Print / PDF`)**: Formal printable credit memo with underwriter sign-off blocks.
* **Theme Switching (`T`)**: Dark / Light workstation mode.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `1` – `5` | Switch active borrower persona |
| `C` | Toggle Side-by-Side Comparison Matrix |
| `R` | Re-run investigation (bypass cache) |
| `T` | Toggle Dark / Light Theme |
| `?` | Show Keyboard Shortcuts Overlay |
| `Esc` | Close active modal or drawer |

---

## 🛠️ Development & Build

### 1. Development Mode (with Vite Dev Server)
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173` and proxies `/api` to `http://127.0.0.1:8000`.

### 2. Build for Production / FastAPI Demo Server
```bash
cd frontend
npm run build
```
Builds the bundle directly into `demo_app/static/`, enabling `python -m demo_app` to serve the full interactive UI.
