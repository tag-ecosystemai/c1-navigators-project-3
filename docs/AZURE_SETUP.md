# Azure OpenAI setup

Azure OpenAI is the primary path of this project. Every LLM call (policy embeddings, policy-rule
extraction, the written explanation, the analyst agent) reads the same five variables from `.env`
in the repo root. No code change is needed once they are filled in.

## 1. What the team lead must give you

| `.env` variable | What it is | Where to find it |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | `https://<resource-name>.openai.azure.com/` (nothing after `.com/`) | Azure portal > your Azure OpenAI resource > *Keys and Endpoint* |
| `AZURE_OPENAI_API_KEY` | Key 1 or Key 2 | same page |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Name of a **chat** deployment that supports JSON mode (gpt-4o-mini or gpt-4o) | Azure AI Foundry > *Deployments* (the deployment **name**, not the model name) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Name of an **embeddings** deployment (text-embedding-3-small) | same list |
| `AZURE_OPENAI_API_VERSION` | Default `2024-10-21` is fine unless the lead says otherwise | |

The two deployments must be created in the same resource as the endpoint and key.

## 2. Put them in `.env` (Git Bash, repo root)

```bash
cp .env.example .env        # skip if you already have a .env
```

Edit `.env` (it is gitignored; never commit it, never paste the key into chat or screenshots):

```
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=<chat deployment name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<embeddings deployment name>
RAG_EMBEDDINGS=azure        # an older .env may still say "local": change it
RAG_LLM=azure
```

## 3. Verify with doctor

```bash
python -m ai_engineering.rag.cli doctor
```

It prints one line per check and exits non-zero if any check fails. A healthy run looks like:

```
Mode: Azure OpenAI: chat=<chat deployment>, embeddings=<embeddings deployment>

[PASS] env AZURE_OPENAI_ENDPOINT: set
[PASS] env AZURE_OPENAI_API_KEY: set
[INFO] deployments in use: chat=..., embeddings=..., api-version=2024-10-21
[PASS] RAG_EMBEDDINGS: azure
[PASS] RAG_LLM: azure
[PASS] embeddings deployment: <name> returned a 1536-dimension vector
[PASS] chat deployment: <name> answered a JSON-mode request
[PASS] policy index: built with azure:<embeddings deployment>

All checks passed.
```

The key and endpoint are never printed. `[WARN] policy index` means there is no index yet; it is built
automatically the first time it is needed. If the index was built offline or with another embeddings
deployment, `scripts/demo.py` rebuilds it for you; to do it by hand:
`python -m ai_engineering.rag.cli ingest`.

Then run the demo: `python scripts/demo.py --persona CUST-GOLD-001` (see `docs/DEMO.md`).

## 4. Common errors

| What you see | Cause | Fix |
|---|---|---|
| `[FAIL] env AZURE_OPENAI_API_KEY: unset` | Key missing or `.env` not in the repo root | Fill it in; `.env` must sit next to `README.md` |
| `[FAIL] endpoint format ... placeholder` | Endpoint still `https://<your-resource>...` | Paste the real endpoint |
| `[FAIL] endpoint format ... should be only https://...` | Endpoint includes `/openai/deployments/...` or `?api-version=` | Keep only `https://<resource>.openai.azure.com/` |
| `[FAIL] RAG_EMBEDDINGS: local` | The system would run offline | Set `RAG_EMBEDDINGS=azure` (and `RAG_LLM=azure`) |
| `no embedding deployment named '...'` / `no chat deployment named '...'` (DeploymentNotFound, 404) | The name in `.env` is not a deployment in this resource | Use the **deployment name** from Foundry > Deployments; check for typos and that it is in the same resource |
| `rejected the API key (401)` | Wrong or regenerated key, or key from a different resource | Copy Key 1 again from *Keys and Endpoint* of the resource that owns the endpoint |
| `rate limit or quota reached (429)` | Tokens-per-minute quota exhausted or very low on the deployment | Wait a minute and retry; ask the lead to raise the deployment's TPM quota; for a live demo, run `--all` only once and keep the HTML reports |
| `timed out` / `Could not connect` | Network, VPN or proxy | Check connectivity to the endpoint; raise `RAG_AZURE_TIMEOUT`; fall back to `--offline` |
| `did not return valid JSON` | The chat deployment's model has no JSON mode | Use gpt-4o-mini or gpt-4o |
| `[FAIL] policy index ... built with 'local-hashing...'` | Index was built offline | `python -m ai_engineering.rag.cli ingest` (the demo does this automatically) |

Azure errors are always shown as these plain-English messages; the raw SDK text (which could contain
request details) is not printed.

## 5. Optional: Azure AI Search instead of the local index

Not used by default. The local numpy + BM25 index already does hybrid search, so only enable this if you
want the index in Azure.

1. Create an Azure AI Search service; copy its endpoint and an admin key.
2. `pip install azure-search-documents` (it is commented out in `ai_engineering/requirements.txt`).
3. Add to `.env`:
   ```
   RAG_STORE=azure_search
   AZURE_SEARCH_ENDPOINT=https://<search-name>.search.windows.net
   AZURE_SEARCH_API_KEY=<admin key>
   AZURE_SEARCH_INDEX=credit-policies
   ```
4. `python -m ai_engineering.rag.cli ingest` (this **deletes and re-creates** the `credit-policies` index),
   then `python -m ai_engineering.rag.cli doctor`.

Status: `AzureSearchStore` is covered by tests against a mock of the SDK only
(`ai_engineering/tests/test_azure_search.py`); it has not been run against a real search service. The
doctor does not probe the Search index.
