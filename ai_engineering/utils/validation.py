import math
from .error_handler import log_error
from .time_utils import parse_datetime

TOP_LEVEL = {"application", "transactions", "documents", "policies", "ml", "context"}


def number(value, allow_zero=True):
    if isinstance(value, bool): return None
    try: result = float(value)
    except (TypeError, ValueError): return None
    return result if math.isfinite(result) and (allow_zero or result > 0) else None


def first(mapping, *keys):
    for key in keys:
        if isinstance(mapping, dict) and key in mapping and mapping[key] is not None: return mapping[key]
    return None


def validate_input(value):
    errors = []
    if not isinstance(value, dict):
        return {key: {} if key != "transactions" else [] for key in TOP_LEVEL}, [log_error("malformed_input", "codex_input must be a dictionary", "validation")]
    extra = set(value) - TOP_LEVEL
    if extra: errors.append(log_error("malformed_input", "unexpected top-level fields", "validation"))
    data = {key: value.get(key, [] if key == "transactions" else {}) for key in TOP_LEVEL}
    if not isinstance(data["application"], dict): data["application"] = {}; errors.append(log_error("malformed_input", "application must be a dictionary", "validation"))
    if not isinstance(data["transactions"], list): data["transactions"] = []; errors.append(log_error("malformed_input", "transactions must be a list", "validation"))
    for key in ("documents", "policies", "ml", "context"):
        if not isinstance(data[key], dict): data[key] = {}; errors.append(log_error("missing_data", key + " missing or invalid", "validation"))
    return data, errors


def valid_transaction(transaction):
    if not isinstance(transaction, dict) or number(transaction.get("amount")) is None: return False
    return parse_datetime(first(transaction, "timestamp", "date")) is not None
