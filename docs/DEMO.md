# Demo guide

## Fresh clone on Windows (Git Bash)

```bash
git clone <repo-url> && cd <repo-folder>
git checkout feat/azure-demo            # or main once merged
python -m venv .venv
source .venv/Scripts/activate
pip install -r ai_engineering/requirements.txt
cp .env.example .env                    # then fill in the Azure values: docs/AZURE_SETUP.md
python -m ai_engineering.rag.cli doctor # must end with "All checks passed."
python -m pytest ai_engineering/tests -q
```

Without Azure values you can still run everything except the Azure parts: use `--offline`.

## Commands

| Goal | Command |
|---|---|
| One persona on Azure (default when the `AZURE_OPENAI_*` variables are set) | `python scripts/demo.py --persona CUST-GOLD-001` |
| All five personas | `python scripts/demo.py --all` |
| Make Azure mandatory (stops with the preflight output if it is not working) | add `--require-azure` |
| Safety net, no Azure at all | `python scripts/demo.py --all --offline` |
| Ask the analyst agent (Azure only) | `python scripts/ask_agent.py` or `python scripts/ask_agent.py -q "Why was CUST-GOLD-002 declined? Cite the policy."` |
| Check the setup | `python -m ai_engineering.rag.cli doctor` |

Every console report and every `demo_output/<applicant_id>.html` starts with the mode banner:
`Azure OpenAI: chat=<deployment>, embeddings=<deployment>` or `OFFLINE MODE - no Azure`.
`demo_output/` is gitignored; open the HTML files in a browser (they have no external assets).

**Before you go on stage:** run `python scripts/demo.py --all` once on the real network, so the
policy index and the rule cache are built and you know every persona works. Keep the HTML reports open
in tabs as a backup.

## 3-minute script

The verdict always comes from the rule engine (the decision matrix in `data/policies/04_...`). Azure
OpenAI reads the policy text, cross-checks the engine, writes the explanation and answers questions;
it never changes the verdict, and a human analyst decides.

**0:00 - Setup line (15 s).** Show the banner. *"This is running on Azure OpenAI: chat deployment X,
embeddings deployment Y. It is decision support; the analyst decides."*

**0:15 - Clean applicant (40 s).** `python scripts/demo.py --persona CUST-GOLD-001`
- Verdict `ELIGIBLE_FOR_APPROVAL`, "All policy checks satisfied". Point at the rules table: 14 rules,
  each with the applicant's actual value (DTI 18.3%, NDI $1,183 against a $800 buffer).
- *"Nothing to investigate. The explanation underneath is written by Azure from these facts only and cites
  the rule codes."*

**0:55 - Income discrepancy, decline (60 s).** `python scripts/demo.py --persona CUST-GOLD-002`
- Verdict `DECLINE_RECOMMENDED`, driver `POL-INC-001`: declared income $7,500 but bank deposits support
  far less (variance 57.3%). The matrix says a variance above 25% is a decline.
- On Azure, show the **Policy RAG checker vs rule evaluator** table: the cited clause for `POL-INC-001`
  and whether the RAG reading agrees. *"The engine and the policy text agree, and here is the exact clause."*
  (Offline you see the retrieved policy paragraph for `POL-INC-001` instead.)

**1:55 - Undisclosed debt, review (45 s).** `python scripts/demo.py --persona CUST-GOLD-004`
- Verdict `FURTHER_REVIEW_REQUIRED`. Point at **two** flagged rows: `POL-TXN-003` (undisclosed
  debt, $740/month found in the bank statement, none declared) and `POL-NDI-001` (disposable income
  $591.74 against a $1,000 buffer for 2 dependents). The "primary driver" line shows `POL-NDI-001`
  because it is the first non-clean rule in the list; say that the undisclosed debt is the story.
- *"The policy gives no automatic verdict for hidden debt, so the engine sends it to a person."*

**2:40 - One question to the agent (20 s).**
`python scripts/ask_agent.py -q "Why was CUST-GOLD-002 declined? Cite the policy."`
- It calls `get_case_report` and `search_policies` and answers with rule codes. Say *"it can only answer
  from those tools and cannot change a decision."*

## If something fails

| Symptom | What to do / say |
|---|---|
| `preflight FAILED` at the start | Read the `[FAIL]` line and its `fix:`. Most likely a deployment name or key. If it cannot be fixed in a minute: `--offline`, and say so: *"The banner says offline mode: this is the safety net without Azure."* |
| 429 / quota in a report | Wait 60 s and rerun that persona; or show the HTML reports you generated beforehand. |
| `RAG checker unavailable: ...` in the Azure section | The rest of the report is still valid (it comes from the rule engine). Say the cross-check is optional and the engine does not depend on it. |
| Explanation shows `Generated from rules, not by an LLM` plus a NOTE | The Azure explanation failed validation or errored; the template is built from the same facts. Nothing is wrong with the decision. |
| `ML scoring unavailable: ...` | Known and expected today: `models/risk_model.pkl` was trained on 20 features, the engine supplies 8 (and `xgboost` must be installed). Say ML scoring is wired but disabled until the feature set is aligned. Do not retrain on stage. |
| `ask_agent.py` fails | Skip it; show the `CUST-GOLD-002` HTML report and read the cited clause instead. |
| Wi-Fi down | `--offline` is designed for this. The banner and every HTML page say OFFLINE MODE. |
| `import sklearn` / DLL blocked error on Windows | `pip install "scikit-learn<1.9.1"`. It only affects the ML probe; everything else runs. |
