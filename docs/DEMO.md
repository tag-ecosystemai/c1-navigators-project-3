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
- Verdict `FURTHER_REVIEW_REQUIRED`, primary driver `POL-TXN-003` (undisclosed debt: $740/month found in
  the bank statement, none declared). The driver is the most severe non-clean rule. A second row,
  `POL-NDI-001` (disposable income $591.74 against a $1,000 buffer for 2 dependents), is also flagged.
- *"The policy gives no automatic verdict for hidden debt, so the engine sends it to a person."*

**2:40 - One question to the agent (20 s).**
`python scripts/ask_agent.py -q "Why was CUST-GOLD-002 declined? Cite the policy."`
- It calls `get_case_report` and `search_policies` and answers with rule codes. Say *"it can only answer
  from those tools and cannot change a decision."*

**About the ML score (if asked).** It is a second opinion, never the verdict. The model was trained on
these same 50 synthetic applicants to predict "decline", so its scores are in-sample (the engine reproduces
them exactly: `python scripts/check_ml_parity.py`). It rates `CUST-GOLD-002` low risk (0.05) even though the
rules recommend decline, because the declared-vs-actual income gap is not what the model learned from. Say
that this is why a human reads both.

## If something fails

| Symptom | What to do / say |
|---|---|
| `preflight FAILED` at the start | Read the `[FAIL]` line and its `fix:`. Most likely a deployment name or key. If it cannot be fixed in a minute: `--offline`, and say so: *"The banner says offline mode: this is the safety net without Azure."* |
| 429 / quota in a report | Wait 60 s and rerun that persona; or show the HTML reports you generated beforehand. |
| `RAG checker unavailable: ...` in the Azure section | The rest of the report is still valid (it comes from the rule engine). Say the cross-check is optional and the engine does not depend on it. |
| Explanation shows `Generated from rules, not by an LLM` plus a NOTE | The Azure explanation failed validation or errored; the template is built from the same facts. Nothing is wrong with the decision. |
| `ML risk score ... precomputed batch prediction` | Live scoring could not run (usually `xgboost` or `scikit-learn` not installed). The number is the stored batch prediction from `data/processed/ml_predictions.csv`, and the line says so; say that too. `ML scoring unavailable: ...` means there is no stored row either. Do not retrain on stage. |
| `ask_agent.py` fails | Skip it; show the `CUST-GOLD-002` HTML report and read the cited clause instead. |
| Wi-Fi down | `--offline` is designed for this. The banner and every HTML page say OFFLINE MODE. |
| `import sklearn` / DLL blocked error on Windows | `pip install "scikit-learn<1.9.1"`. It only affects the ML probe; everything else runs. |

## Demo app (web UI)

A single-page web app on top of the same engine. It only displays what `investigate()` and the agents return, so
the verdicts are identical to the console demo. Nothing secret reaches the browser (the page never sees the API
key or the endpoint).

### Start it

```bash
python -m demo_app                 # http://127.0.0.1:8000, Azure OpenAI if configured, else offline
python -m demo_app --offline       # safety net, no Azure at all
python -m demo_app --port 8080     # another port;  --no-warm skips the pre-run
```

On start it checks Azure first (a few seconds), prints `Mode: Azure OpenAI live: chat=..., embeddings=...` or
`Mode: OFFLINE MODE - no Azure`, then pre-runs the five customers in the background (about a minute on Azure).
The page shows "Warming up. N of 5 customers are ready" until that finishes; after that every click is instant.
**Start it two minutes before you present.** Open http://127.0.0.1:8000 in Chrome or Edge, full screen (F11).

The header always shows the mode: green **Azure OpenAI live** or amber **Offline mode** (with the reason in a
banner when Azure was expected). Keys: `1` to `5` run a customer, `C` opens Compare, `T` switches the theme.
Set `DEMO_AZURE_TIMEOUT` (seconds, default 60) if your Azure resource is slow.

### Demo order (about 3 minutes)

| Time | Do | Say |
|---|---|---|
| 0:00 | Point at the badge and the line "Decision support only" | "Four agents on Azure OpenAI. The system recommends, a person decides." |
| 0:15 | Press `2` (Marcus Vance). Click **Why this verdict?** | "Decline: he declared $7,500 a month but the bank deposits show far less, a 57.3% gap, over the 25% limit. The rule is the driver; the row opens with the policy text." |
| 1:05 | Press `4` (David O'Connor). Open the cross-check panel | "Review, not decline: $740 a month of hidden loan payments. The policy gives no automatic verdict for that, so a person decides. The policy checker agreed with the rule engine on all 11 rules it compared." |
| 1:50 | Press `1` (Sarah Jenkins). Look at the cross-check panel | "Eligible. The honest part: on net disposable income the policy checker disagreed with the rule engine, because that rule is a formula with a per-dependent amount. We show it, with the clause, instead of hiding it." |
| 2:30 | Press `C` | "Side by side: same engine, three outcomes. The ML score is a supporting signal and never changes the verdict." |

Other things to point at: the four agent steps with real timings, the green/amber/red chips (each with an icon and
text), the explanation source label ("Written by Azure OpenAI" or "Template"), and the analyst checklist.

### If something fails

| Symptom | What to do |
|---|---|
| Badge is amber "Offline mode" and a banner gives a reason | The verdict, rules and ML score are unchanged; only the policy checker and the Azure explanation are skipped and labelled. Say so: "Azure is not answering, so this is the offline safety net." Click **Run again** after about 20 seconds to retry Azure. |
| One customer is slow (over 15 seconds) | It is a cold Azure call; the app falls back by itself after the time limit. Move on and come back. |
| Banner "Cannot reach the demo server" | The server stopped. Restart `python -m demo_app` (add `--offline` if Azure is the problem). |
| "address already in use" | Another copy is running: close it, or use `--port 8081`. |
| Page looks blank or old | Hard refresh with Ctrl+F5. |
| Text too small on the projector | Browser zoom Ctrl and plus; the layout adapts. |
| Nothing works | Run `python scripts/demo.py --all --offline` and open the HTML reports in `demo_output/`. |

Limits shown on each rule are the rule engine's own (for example the loan-to-income cap per credit tier), so they
always match the status next to them.
