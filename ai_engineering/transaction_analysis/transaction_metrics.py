from datetime import timedelta


def gambling_metrics(transactions, income):
    amounts = [t["amount"] for t in transactions if t["category"] in {"GAMBLING", "BETTING", "CASINO"} and t["type"] == "DEBIT"]
    total = sum(amounts); return {"gambling_total_amount": total, "gambling_pct_of_income": None if not income else total / income * 100}


def nsf_events(transactions): return sum(1 for t in transactions if t["category"] in {"NSF", "OVERDRAFT"})


def undisclosed_debt(transactions):
    amounts = [t["amount"] for t in transactions if t["category"] == "DEBT_SERVICE_UNDISCLOSED" and t["type"] == "DEBIT"]
    return sum(amounts) / 3 if amounts else 0.0


def window_dressing(transactions, income, application_date):
    if not income or application_date is None: return []
    start = application_date - timedelta(days=14)
    return [{"timestamp": t["timestamp"].isoformat(), "amount": t["amount"], "category": t["category"]} for t in transactions if start <= t["timestamp"] <= application_date and t["type"] == "CREDIT" and t["category"] in {"TRANSFER", "DEPOSIT", "CASH_IN"} and t["amount"] > income * .5]


def burn_rate(transactions):
    payrolls = [t for t in transactions if t["category"] == "PAYROLL" and t.get("running_balance") is not None]
    if not payrolls: return "MISSING_DATA"
    for pay in payrolls:
        salary = pay["amount"]
        later = [t for t in transactions if pay["timestamp"] < t["timestamp"] <= pay["timestamp"] + timedelta(days=7) and t.get("running_balance") is not None]
        if any(float(t["running_balance"]) < salary * .1 for t in later): return "CRITICAL_DISTRESS"
    all_balances = [float(t["running_balance"]) for t in transactions if t.get("running_balance") is not None]
    return "VULNERABLE" if all_balances and min(all_balances) < payrolls[-1]["amount"] * .2 else "HEALTHY"


def analyse_transactions(input_data):
    from .transaction_cleaner import clean_transactions
    from ..utils.validation import first, number
    from ..utils.time_utils import parse_datetime
    from ..utils.error_handler import log_error, module_result
    from ..utils.evidence_builder import build_evidence
    try:
        transactions, invalid = clean_transactions(input_data["transactions"])
        errors = [log_error("malformed_input", text, "transaction_metrics") for text in invalid]
        if not transactions: errors.append(log_error("missing_data", "no valid transactions", "transaction_metrics"))
        income = number(first(input_data["application"], "income", "declared_monthly_net_income"), False)
        application_date = parse_datetime(input_data.get("context", {}).get("timestamp"))
        gambling = gambling_metrics(transactions, income)
        data = {**gambling, "nsf_event_count": nsf_events(transactions), "undisclosed_debt_total": undisclosed_debt(transactions),
                "window_dressing_events": window_dressing(transactions, income, application_date), "burn_rate_status": burn_rate(transactions)}
        evidence = [build_evidence("EV-TXN-GAMBLING", "transaction_pattern", "Gambling activity", "Calculated gambling activity.", "transaction_metrics", gambling, "high" if (gambling["gambling_pct_of_income"] or 0) > 10 else "low")]
        return module_result("transaction_metrics", data, evidence, errors)
    except Exception as exc:
        return module_result("transaction_metrics", {}, [], [log_error("analysis_failure", str(exc), "transaction_metrics")], "fallback")
