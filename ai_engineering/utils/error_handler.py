import logging
from .time_utils import iso_timestamp

LOGGER = logging.getLogger(__name__)
VALID_CATEGORIES = {"missing_data", "malformed_input", "analysis_failure", "policy_failure", "ml_failure", "system_failure"}


def log_error(category: str, message: str, module: str) -> dict:
    category = category if category in VALID_CATEGORIES else "system_failure"
    error = {"category": category, "message": str(message), "module": module, "timestamp": iso_timestamp()}
    LOGGER.error("%s: %s", module, message)
    return error


def module_result(module: str, data=None, evidence=None, errors=None, status="ok") -> dict:
    return {"status": "fallback" if status == "fallback" or errors else "ok", "data": data or {},
            "evidence": evidence or [], "errors": errors or [], "module": module, "timestamp": iso_timestamp()}
