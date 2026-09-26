# Policy RAG

Retrieves lending-policy and regulatory passages with citations, and checks an application
against them. It covers PRD section 5.4 (Lending Policy Check) and the "RAG" and "Vector DB"
parts of the architecture.

```
data/policies/*.pdf|docx|md|txt
      │  loaders.py      read files, detect headings and page numbers
      ▼
  chunking.py            one chunk per section (split at paragraphs if long), with clause numbers
      ▼
  embeddings.py          Azure OpenAI (real) or offline hashing embedder (dev/tests)
      ▼
  stores.py              local numpy + BM25 index, or Azure AI Search; both do hybrid search
      ▼
  retriever.py           PolicyRetriever.search("max DTI?") -> passages + citations
      ▼
  policy_checker.py      retrieve clauses -> LLM extracts rules -> Python evaluates them
      ▼                  -> satisfied / not_satisfied / unclear / missing per requirement
  tools.py               search_policies + check_policy_compliance for agent tool-calling
```

## Setup (run from the repo root)

```bash
python -m venv .venv
# Windows (Git Bash): source .venv/Scripts/activate    PowerShell: .venv\Scripts\Activate.ps1
pip install -r ai_engineering/requirements.txt
cp .env.example .env        # then fill in the Azure OpenAI values
```

## Commands

```bash
python -m ai_engineering.rag.cli ingest                              # build the index from data/policies
python -m ai_engineering.rag.cli search "maximum debt to income"     # try a query
python -m ai_engineering.rag.cli eval                                # retrieval hit rate on the question set
python -m ai_engineering.rag.cli check data/test_cases/sample_application.json   # needs Azure OpenAI
python -m pytest ai_engineering/tests -q                             # offline tests, no keys needed
```

No Azure keys yet? Set `RAG_EMBEDDINGS=local` in `.env` to use `ingest`, `search` and `eval`
offline. After you switch embedders, run `ingest` again; the retriever refuses to search an
index built with a different embedder.

## Using it from the agent / FastAPI

```python
from ai_engineering.rag.tools import POLICY_TOOL_SCHEMAS, call_policy_tool, search_policies

search_policies("What documents must a self-employed applicant provide?")
# {"query": ..., "results": [{"citation": "... > 2 Applicant eligibility (clause 2.1, ...)", "text": ..., "score": ...}]}

# In the agent loop, add POLICY_TOOL_SCHEMAS to the tools list and dispatch with:
call_policy_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
```

## Design decisions (useful for the presentation)

- **The LLM reads the rule, Python applies it.** The LLM only turns policy text into structured
  rules (`debt_to_income <= 0.40`). The comparison itself is plain code, so results are
  reproducible and auditable. The LLM never decides whether the applicant passes.
- **Grounding checks.** A rule is dropped if it cites a chunk that was not retrieved. Every rule
  carries a verbatim quote, and `quote_verified` says whether the quote really appears in the source.
- **Four statuses from the PRD.** `missing` = no data for the requirement, `unclear` = needs
  analyst judgement or can't be compared, otherwise `satisfied` / `not_satisfied`.
  `severity` shows whether a failure breaches policy, triggers a referral, or is a risk indicator.
- **Hybrid search.** Keyword search (BM25) catches exact terms like "DTI" or "620"; embeddings
  catch paraphrases. The two rankings are merged with reciprocal rank fusion.
- **Section-aware chunks.** Chunks never cross a heading, so citations name a section and clause.
- **Rule cache.** Extracted rules are cached in `data/processed/policy_index/rules_cache/`, so the
  same case gives the same answer in the demo, and the team can open the JSON and review the rules.

## Policy documents

`data/policies/` holds the four real Navigators policy files (eligibility, affordability,
transaction investigation, referral/decision matrix). Rule codes such as `POL-DTI-001` are
what the checker cites — `loaders.py` promotes the "Document Code: POL-RET-2026-0N: ..."
heading to the document title (the four files share a generic H1), and `chunking.py` reads
rule codes from headings as well as body text, since the real files state a chunk's own code
only in its heading. Both `POL-XXX-NNN` codes and numbered clauses ("3.1") are recognised, so
any additional regulation document (Basel, CFPB, etc.) can use either style.

Sub-folders become categories you can filter by, e.g. `data/policies/regulation/` →
`search_policies(q, category="regulation")`.

**Multi-field formulas are a known gap.** POL-DTI-001, POL-LTI-001, POL-NDI-001, POL-INC-001
and the POL-TXN-003 "Shadow DTI" are each a formula over *several* raw fields (e.g. NDI =
income − rent − existing debt − new payment). The checker only compares *one* application
field against a threshold; it can't evaluate a formula itself. `applications.csv` already
gives us `calculated_dti_pct` and `calculated_lti_ratio` pre-computed, which is exactly the
right pattern — confirm with Ruffy/the financial-analysis tool that NDI and income-variance
get computed the same way upstream (e.g. `net_disposable_income`, `income_variance_pct`)
before being passed into `check_policy_compliance`. Otherwise those rules will always come
back `missing`, as they do now in `sample_application.json` (which has no such fields yet).

POL-DTI-001 also has **4 bands, not 2** (`<=35` satisfied, `35.1–43` conditional pass, `43.1–50`
mandatory referral, `>50` decline) — the system prompt's example only showed a 2-band split.
Skim the LLM's actual rule extraction once Azure keys are in (`cli check --json`) and check it
produced three boundary rules for POL-DTI-001, not just one; `data/processed/policy_index/rules_cache/`
holds the cached JSON so it's easy to inspect and correct the prompt if needed.

## Application fields

Field names in `data/test_cases/sample_application.json` and `DEFAULT_TOPICS` in
`policy_checker.py` are matched to `DATA_DICTIONARY.md`'s `applications.csv` schema
(`calculated_dti_pct`, `calculated_lti_ratio`, `credit_score`, `employment_length_months`,
`bankruptcies_count`, `tax_liens_count`, etc.) — pass a flat dict of those fields (plus any
transaction-derived aggregates the anomaly-detection tool computes, and the formula fields
above) to `check_policy_compliance`.

## Still needed from the team

- `data/test_cases/golden_demo_cases.json` and a few rows of `applications.csv` /
  `transactions.csv` — to run the 5 golden personas through `check_policy_compliance` and
  confirm the flagged rules match each persona's `expected_verdict`. This is the strongest
  evidence for the presentation: real precision/recall against ground truth, not a guess.
- Confirmation of the NDI / income-variance / shadow-DTI field names, per the gap above.
- Azure OpenAI keys, to run `cli check` for real and verify the LLM's rule extraction
  (this has only been tested with a scripted stand-in for the LLM so far, `FakeLLM` in
  `ai_engineering/tests/test_rag.py`).
