from .statistical_models import z_score
from ..utils.error_handler import log_error, module_result
from ..utils.evidence_builder import build_evidence
from ..utils.validation import number, valid_transaction


def analyse_anomalies(input_data, transaction_data):
    try:
        amounts = [number(t.get("amount")) for t in input_data["transactions"] if valid_transaction(t)]
        amounts = [v for v in amounts if v is not None]
        flags = [t for t in input_data["transactions"] if isinstance(t, dict) and t.get("flagged_anomaly")]
        score = None if not amounts else min(100.0, (max(z_score(amounts, v) for v in amounts) * 20) + len(flags) * 10)
        data = {"anomaly_score": score, "anomaly_count": len(flags), "unusual_transaction_patterns": len(flags) > 0}
        evidence = [build_evidence("EV-ANOM-001", "anomaly_flag", "Transaction anomaly", "Anomalous transactions were flagged.", "anomaly_scoring", {"anomaly_score": score, "anomaly_count": len(flags)}, "high" if (score or 0) >= 50 else "low")] if flags else []
        errors = [] if score is not None else [log_error("missing_data", "no valid transactions for anomaly analysis", "anomaly_scoring")]
        return module_result("anomaly_scoring", data, evidence, errors)
    except Exception as exc:
        return module_result("anomaly_scoring", {}, [], [log_error("analysis_failure", str(exc), "anomaly_scoring")], "fallback")
