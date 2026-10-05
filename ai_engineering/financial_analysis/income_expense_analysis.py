from ..utils.validation import first, number, valid_transaction


def proposed_payment(application):
    amount, months, rate = number(first(application, "requested_amount", "requested_loan_amount")), number(application.get("loan_term_months")), number(application.get("interest_rate_pct"))
    if None in (amount, months, rate) or months <= 0: return None
    monthly_rate = rate / 1200
    return amount / months if monthly_rate == 0 else amount * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def verified_monthly_inflows(transactions):
    credits = [number(t.get("amount")) for t in transactions if valid_transaction(t) and str(t.get("type", "")).upper() == "CREDIT" and str(t.get("category", "")).upper() in {"PAYROLL", "RECURRING_CREDIT"}]
    credits = [v for v in credits if v is not None]
    return sum(credits) / 3 if credits else None


def income_variance(application, transactions):
    declared = number(first(application, "income", "declared_monthly_net_income"), False)
    verified = verified_monthly_inflows(transactions)
    return None if declared is None or verified is None else abs(declared - verified) / declared * 100


def net_disposable_income(application, payment):
    fields = [number(first(application, "income", "declared_monthly_net_income"), False), number(first(application, "declared_monthly_housing_expense", "housing_expense")), number(first(application, "declared_monthly_living_expenses", "living_expenses")), number(first(application, "declared_existing_monthly_debt", "existing_monthly_debt")), payment]
    return None if any(value is None for value in fields) else fields[0] - sum(fields[1:])
