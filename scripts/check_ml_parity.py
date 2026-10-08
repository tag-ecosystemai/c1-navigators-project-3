"""Does live ML scoring in the engine reproduce data/processed/ml_predictions.csv?

For every applicant in that file, run investigate() (ML enabled) on the application from
applications.json plus its transactions from transactions.json, and compare the engine's risk score
with the precomputed predicted_pd. Needs xgboost (pip install -r ai_engineering/requirements.txt).

    python scripts/check_ml_parity.py [--tolerance 1e-6]

Note: the model was trained on these same 50 applicants, so a match proves the engine builds the
training features correctly; it says nothing about accuracy on new applicants.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_engineering.ml_scoring.ml_integration import level_for  # noqa: E402
from ai_engineering.orchestrator.orchestrator import investigate  # noqa: E402
from ai_engineering.rag import mode  # noqa: E402

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    mode.force_offline()  # this check is about ML only: keep the RAG/Azure cross-check out of it

    expected = {r["applicant_id"]: float(r["predicted_pd"]) for r in csv.DictReader(open(PROCESSED / "ml_predictions.csv", encoding="utf-8"))}
    apps = {a["applicant_id"]: a for a in json.loads((PROCESSED / "applications.json").read_text(encoding="utf-8"))}
    txns: dict[str, list] = {}
    for t in json.loads((PROCESSED / "transactions.json").read_text(encoding="utf-8")):
        txns.setdefault(t["applicant_id"], []).append(t)

    compared, matched, level_matched, skipped, diffs = 0, 0, 0, [], []
    for applicant_id, truth in expected.items():
        if applicant_id not in apps or applicant_id not in txns:
            skipped.append((applicant_id, "no application or transactions in the JSON files"))
            continue
        ml = investigate({"application": apps[applicant_id], "transactions": txns[applicant_id], "ml": {"enabled": True}})["ml"]
        if ml.get("risk_score") is None:
            skipped.append((applicant_id, "engine produced no score (ML unavailable)"))
            continue
        compared += 1
        diff = abs(ml["risk_score"] - truth)
        matched += diff <= args.tolerance
        level_matched += ml["risk_level"] == level_for(truth)
        if diff > args.tolerance:
            diffs.append((applicant_id, ml["risk_score"], truth, diff))

    print(f"applicants in ml_predictions.csv: {len(expected)}   scored by the engine: {compared}   skipped: {len(skipped)}")
    if compared:
        print(f"score match (|diff| <= {args.tolerance:g}): {matched}/{compared} = {matched / compared:.0%}")
        print(f"risk level match: {level_matched}/{compared} = {level_matched / compared:.0%}")
    for applicant_id, got, truth, diff in diffs:
        print(f"  DIFF {applicant_id}: engine={got:.6f} file={truth:.6f} |diff|={diff:.2e}")
    for applicant_id, why in skipped[:5]:
        print(f"  SKIPPED {applicant_id}: {why}")
    if skipped and not compared:
        print("No applicant could be scored. Is xgboost installed (and scikit-learn < 1.9.1 on Windows)?")
    return 0 if compared and matched == compared else 1


if __name__ == "__main__":
    sys.exit(main())
