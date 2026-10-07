"""Run the golden demo cases through investigate() and the policy RAG cross-check.

    python scripts/run_golden_rag.py            # uses Azure OpenAI if configured
    python scripts/run_golden_rag.py --verbose  # also list every conflicting rule

investigate() already runs the cross-check (report["policy_cross_check"]); this script
reads it from there, so each case calls the RAG side once. If Azure is not configured
the table still prints, with the RAG columns marked unavailable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_engineering.orchestrator.orchestrator import investigate  # noqa: E402

CASES = ROOT / "data" / "test_cases" / "golden_demo_cases.json"
TRANSACTIONS = ROOT / "data" / "processed" / "transactions.json"
# Answer-key fields: must never reach the engine or the RAG prompt.
LABEL_FIELDS = {"expected_verdict", "persona_type", "notes"}


def _table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))  # noqa: E731
    return "\n".join([line(headers), line(["-" * w for w in widths])] + [line(r) for r in rows])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="print the conflicting rules in detail")
    args = parser.parse_args()

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    all_txns = json.loads(TRANSACTIONS.read_text(encoding="utf-8"))

    rows, details = [], []
    for case in cases:
        application = {k: v for k, v in case.items() if k not in LABEL_FIELDS}
        txns = [t for t in all_txns if t.get("applicant_id") == case["applicant_id"]]
        result = investigate({"application": application, "transactions": txns})

        report = result["report"]
        verdict = report["final_decision"]["verdict"]
        check = report["policy_cross_check"]
        if check["available"]:
            counts = Counter(r.get("rag_outcome") or "none" for r in check["rules"].values())
            rag = " ".join(f"{k}={counts[k]}" for k in ("pass", "review", "fail", "missing") if counts[k])
            conflicts = ", ".join(check["conflicts"]) or "-"
        else:
            rag, conflicts = "unavailable", "-"
            details.append(f"{case['applicant_id']}: RAG unavailable ({check['error']})")
        expected = case["expected_verdict"]
        rows.append([case["persona_type"], expected, f"{verdict}{'' if verdict == expected else '  <-- MISMATCH'}", rag, conflicts])
        for code in check["conflicts"]:
            rule = check["rules"][code]
            details.append(
                f"{case['applicant_id']} {code}: evaluator={rule['evaluator']} rag={rule['rag_outcome']} "
                f"({rule['agreement']}) {rule.get('citation')}"
            )

    print(_table(rows, ["persona", "expected_verdict", "engine_verdict", "rag_status_counts", "conflicting_rules"]))
    matches = sum(r[1] == r[2] for r in rows)
    print(f"\nEngine verdict matches expected: {matches}/{len(rows)}")
    if details and (args.verbose or any("unavailable" in d for d in details)):
        print("\n" + "\n".join(details))


if __name__ == "__main__":
    main()
