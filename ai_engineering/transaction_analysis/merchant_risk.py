RISK_CATEGORIES = {"GAMBLING", "BETTING", "CASINO", "NSF", "OVERDRAFT", "DEBT_SERVICE_UNDISCLOSED"}


def risky_merchants(transactions):
    return sorted({str(t.get("merchant", "unknown")) for t in transactions if t.get("category") in RISK_CATEGORIES})
