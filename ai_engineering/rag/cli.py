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
    if not args.json:
        from .mode import banner

        print(f"Mode: {banner(settings)}")
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
        return
    print(f"Requires review: {result.requires_review}   {result.counts}\n")
    for r in result.results:
        print(f"{r.status.upper():<14} [{r.severity}] {r.requirement}")
        print(f"{'':<14} {r.explanation}")
        print(f"{'':<14} Source: {r.citation}{'' if r.quote_verified else '  (quote not verified)'}\n")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Preflight the Azure setup. Prints set/unset for env vars, never their values."""
    from .doctor import format_checks, ok, run_checks

    settings = get_settings()
    checks = run_checks(settings, allow_offline=args.allow_offline)
    print(format_checks(settings, checks))
    if not ok(checks):
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

    d = sub.add_parser("doctor", help="Preflight: env vars, Azure deployments, index (exit 1 on failure)")
    d.add_argument("--allow-offline", action="store_true", help="do not fail when RAG_EMBEDDINGS/RAG_LLM are local")
    d.set_defaults(func=cmd_doctor)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
