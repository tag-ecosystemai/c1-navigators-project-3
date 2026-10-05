from .time_utils import iso_timestamp

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
EVIDENCE_TYPES = {"transaction_pattern", "financial_metric", "policy_violation", "anomaly_flag", "supporting_document", "risk_indicator", "ml_feature", "summary_statistic"}


def build_evidence(identifier, evidence_type, title, description, source, data, severity="low") -> dict:
    return {"id": str(identifier), "type": evidence_type if evidence_type in EVIDENCE_TYPES else "summary_statistic",
            "title": str(title), "description": str(description), "source": str(source),
            "data": data if isinstance(data, dict) else {},
            "severity": severity if severity in SEVERITY_ORDER else "low", "timestamp": iso_timestamp()}


def sort_evidence(items) -> list:
    return sorted((item for item in items if isinstance(item, dict)), key=lambda item: SEVERITY_ORDER.get(item.get("severity"), 3))
