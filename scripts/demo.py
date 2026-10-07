"""Live demo: run a golden persona through the investigation engine and print/write the report.

    python scripts/demo.py --persona CUST-GOLD-001        # one persona
    python scripts/demo.py --all                          # all five
    python scripts/demo.py --all --offline                # safety net: no Azure at all
    python scripts/demo.py --persona CUST-GOLD-002 --require-azure

Azure is required (and preflight-checked) by default whenever the AZURE_OPENAI_* variables are set;
if it is not working the demo stops and prints which check failed and how to fix it. --offline forces
the safety-net mode. Both the console and demo_output/<applicant_id>.html state which mode ran.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_engineering.demo.cases import find_case, load_cases, load_transactions, run_case  # noqa: E402
from ai_engineering.demo.explain import explain  # noqa: E402
from ai_engineering.demo.render import console_report, html_report, retrieve_policy_text  # noqa: E402
from ai_engineering.demo.session import PreflightFailed, start_session  # noqa: E402
from ai_engineering.demo.view import build_view  # noqa: E402

OUTPUT_DIR = ROOT / "demo_output"


def run_one(session, case: dict, transactions: list[dict]) -> dict:
    application, result = run_case(case, transactions, ml_enabled=session.ml_enabled)
    view = build_view(case, application, result, session.banner, session.azure_mode, session.ml_reason)
    policy_text = None if session.azure_mode else retrieve_policy_text([r["code"] for r in view["rules"]])
    explanation = explain(view, session.llm)
    print(console_report(view, explanation, policy_text))
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{case['applicant_id']}.html"
    path.write_text(html_report(view, explanation, policy_text), encoding="utf-8")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nHTML report: {shown}\n")
    return view


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    pick = parser.add_mutually_exclusive_group(required=True)
    pick.add_argument("--persona", help="applicant_id (e.g. CUST-GOLD-001) or persona_type")
    pick.add_argument("--all", action="store_true", help="run all golden personas")
    parser.add_argument("--require-azure", action="store_true", default=None,
                        help="fail loudly with the preflight output if Azure is not working (default when Azure env vars are set)")
    parser.add_argument("--offline", action="store_true", help="force the offline safety-net mode (no Azure)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        session = start_session(offline=args.offline, require_azure=args.require_azure)
    except PreflightFailed as exc:
        print(exc, file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for notice in session.notices:
        print(f"NOTE: {notice}")

    cases = load_cases()
    try:
        selected = cases if args.all else [find_case(cases, args.persona)]
    except KeyError as exc:
        print(f"Error: {exc.args[0]}", file=sys.stderr)
        return 2
    transactions = load_transactions()

    views = [run_one(session, case, transactions) for case in selected]

    if args.all:
        print("=" * 78 + f"\n {session.banner}\n" + "=" * 78)
        width = max(len(v["applicant_id"]) for v in views)
        print(f"{'applicant':<{width}}  {'expected_verdict':<24}  {'engine_verdict':<24}  match")
        for v in views:
            print(f"{v['applicant_id']:<{width}}  {v['expected_verdict']:<24}  {v['verdict']:<24}  "
                  f"{'yes' if v['verdict'] == v['expected_verdict'] else 'NO'}")
        print(f"\nEngine verdict matches expected: {sum(v['verdict'] == v['expected_verdict'] for v in views)}/{len(views)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
