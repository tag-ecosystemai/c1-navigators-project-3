from ..utils.validation import first, number, valid_transaction
from ..utils.time_utils import parse_datetime


def clean_transactions(transactions):
    clean, errors = [], []
    for item in transactions:
        if not valid_transaction(item):
            errors.append("malformed transaction skipped"); continue
        value = dict(item); value["amount"] = number(item.get("amount")); value["category"] = str(item.get("category") or "unknown").upper()
        value["type"] = str(item.get("type") or "").upper(); value["timestamp"] = parse_datetime(first(item, "timestamp", "date"))
        clean.append(value)
    return sorted(clean, key=lambda t: t["timestamp"]), errors
