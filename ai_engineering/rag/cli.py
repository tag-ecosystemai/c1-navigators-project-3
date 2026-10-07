"""Command line for the policy RAG pipeline. Run from the repo root:

    python -m ai_engineering.rag.cli ingest
    python -m ai_engineering.rag.cli search "maximum debt to income ratio"
    python -m ai_engineering.rag.cli eval
    python -m ai_engineering.rag.cli check data/test_cases/sample_application.json
    python -m ai_engineering.rag.cli doctor
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import textwrap
from pathlib import Path

from .config import REPO_ROOT, get_settings
from .retriever import PolicyRetriever


def cmd_ingest(args: argparse.Namespace) -> None:
    r = PolicyRetriever(get_settings())
    chunks = r.ingest()
    docs = sorted({c.source for c in chunks})
    print(f"Indexed {len(chunks)} chunks from {len(docs)} document(s) with {r.embedder.name}:")
    for d in docs:
        print(f"  - {d} ({sum(c.source == d for c in chunks)} chunks)")


def cmd_search(args: argparse.Namespace) -> None:
    r = PolicyRetriever(get_settings())
    for i, res in enumerate(r.search(args.query, k=args.k, category=args.category), 1):
        print(f"\n[{i}] {res.chunk.citation}   score={res.score:.4f}")
        print(textwrap.indent(textwrap.shorten(res.chunk.text, 400), "    "))


def cmd_eval(args: argparse.Namespace) -> None:
    """Retrieval quality: does the expected clause appear in the top-k results?"""
    path = Path(args.file) if Path(args.file).is_absolute() else REPO_ROOT / args.file
    cases = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    r = PolicyRetriever(get_settings())
    hits, rr = 0, 0.0
    for case in cases:
        results = r.search(case["question"], k=args.k)
        exp = case["expected_section"]
        rank = next((i for i, res in enumerate(results, 1) if exp in res.chunk.clauses or exp in res.chunk.section), None)
        hits += rank is not None
        rr += 1 / rank if rank else 0
        mark = f"rank {rank}" if rank else "MISS"
        print(f"{mark:>7}  {exp:<6} {case['question']}")
    n = len(cases)
    print(f"\nhit@{args.k}: {hits}/{n} = {hits / n:.0%}    MRR: {rr / n:.3f}")


def cmd_check(args: argparse.Namespace) -> None:
    from .llm import AzureChatLLM
    from .policy_checker import PolicyChecker

    settings = get_settings()
    application = json.loads(Path(args.application).read_text())
    checker = PolicyChecker(PolicyRetriever(settings), AzureChatLLM(settings))
    result = checker.check(application, use_cache=not args.no_cache)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
        return
    print(f"Requires review: {result.requires_review}   {result.counts}\n")
    for r in result.results:
        print(f"{r.status.upper():<14} [{r.severity}] {r.requirement}")
        print(f"{'':<14} {r.explanation}")
        print(f"{'':<14} Source: {r.citation}{'' if r.quote_verified else '  (quote not verified)'}\n")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Check the Azure setup end to end. Prints set/unset for env vars, never their values."""
    import os

    settings = get_settings()
    failures = 0

    def report(ok: bool | None, label: str, detail: str = "", fix: str = "") -> None:
        nonlocal failures
        mark = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        failures += ok is False
        print(f"[{mark}] {label}" + (f": {detail}" if detail else ""))
        if ok is False and fix:
            print(f"       fix: {fix}")

    required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
    optional = ["AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "AZURE_OPENAI_CHAT_DEPLOYMENT"]
    if settings.store_backend.lower() == "azure_search":
        required += ["AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY"]
    for name in required:
        report(bool(os.getenv(name)), f"env {name}", "set" if os.getenv(name) else "unset",
               f"add {name} to .env (copy .env.example to .env)")
    for name in optional:
        print(f"[INFO] env {name}: {'set' if os.getenv(name) else 'unset (default used)'}")

    azure_ready = bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)

    # --- embeddings
    if settings.embeddings_backend.lower() == "azure" and not azure_ready:
        report(None, "embeddings call", "skipped, Azure OpenAI is not configured")
    else:
        try:
            from .embeddings import get_embedder

            embedder = get_embedder(settings)
            vec = embedder.embed(["ping"])
            report(True, "embeddings call", f"{embedder.name}, dimension {vec.shape[1]}")
        except Exception as exc:  # noqa: BLE001
            report(False, "embeddings call", str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__,
                   "check AZURE_OPENAI_EMBEDDING_DEPLOYMENT, the key and the endpoint")

    # --- chat
    if settings.rag_llm.lower() != "azure":
        report(None, "chat call", f"skipped, RAG_LLM={settings.rag_llm}")
    elif not azure_ready:
        report(None, "chat call", "skipped, Azure OpenAI is not configured")
    else:
        try:
            from .llm import AzureChatLLM

            llm = AzureChatLLM(settings)
            llm.complete_json("Reply with a JSON object.", '{"ping": true}')
            report(True, "chat call", llm.name)
        except Exception as exc:  # noqa: BLE001
            report(False, "chat call", str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__,
                   "check AZURE_OPENAI_CHAT_DEPLOYMENT, the key and the endpoint")

    # --- index
    try:
        if settings.store_backend.lower() == "local":
            from .stores import LocalVectorStore

            exists = (LocalVectorStore(settings.index_dir).index_dir / "manifest.json").exists()
        else:
            exists = True  # Azure AI Search index is not probed here
        report(exists, "policy index", str(settings.index_dir) if exists else f"none at {settings.index_dir}",
               "run: python -m ai_engineering.rag.cli ingest (or let the first policy check build it)")
    except Exception as exc:  # noqa: BLE001
        report(False, "policy index", type(exc).__name__, "check RAG_STORE and RAG_INDEX_DIR")

    print("\nAll checks passed." if not failures else f"\n{failures} check(s) failed.")
    if failures:
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="python -m ai_engineering.rag.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest", help="Load, chunk, embed and index data/policies").set_defaults(func=cmd_ingest)

    s = sub.add_parser("search", help="Search the policy index")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--category")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("eval", help="Measure retrieval hit rate on a question set")
    e.add_argument("--file", default="data/test_cases/rag_eval_questions.jsonl")
    e.add_argument("-k", type=int, default=5)
    e.set_defaults(func=cmd_eval)

    c = sub.add_parser("check", help="Check an application JSON against policy (needs Azure OpenAI)")
    c.add_argument("application")
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-cache", action="store_true")
    c.set_defaults(func=cmd_check)

    sub.add_parser("doctor", help="Check env vars, Azure calls and the index").set_defaults(func=cmd_doctor)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
