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
