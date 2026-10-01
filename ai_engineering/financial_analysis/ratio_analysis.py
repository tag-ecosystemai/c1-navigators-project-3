from ..utils.validation import first, number


def dti(application, payment, undisclosed_debt=0.0):
    income = number(first(application, "income", "declared_monthly_net_income"), False)
    debt = number(first(application, "declared_existing_monthly_debt", "existing_monthly_debt"))
    if None in (income, debt, payment): return None
    return (debt + undisclosed_debt + payment) / income * 100


def lti(application):
    amount = number(first(application, "requested_amount", "requested_loan_amount"))
    income = number(first(application, "declared_annual_income"), False)
    return None if amount is None or income is None else amount / income


def credit_tier(score):
    score = number(score)
    if score is None: return None
    return "Tier 1" if score >= 720 else "Tier 2" if score >= 660 else "Tier 3" if score >= 600 else "Tier 4"
