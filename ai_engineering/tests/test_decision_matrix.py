"""Verdict follows the underwriting decision matrix (policy 04); NDI buffer; data gaps vs. real failures."""

from __future__ import annotations

import pytest

from ai_engineering.orchestrator import orchestrator
from ai_engineering.orchestrator.orchestrator import _classify, _decision, investigate
from ai_engineering.policy_engine.policy_evaluator import evaluate_policies, find_data_gaps, ndi_buffer, ndi_status
from ai_engineering.utils.error_handler import log_error, module_result

ELIGIBLE, REVIEW, DECLINE = "ELIGIBLE_FOR_APPROVAL", "FURTHER_REVIEW_REQUIRED", "DECLINE_RECOMMENDED"


@pytest.fixture(autouse=True)
def _no_rag_network(monkeypatch):
    from ai_engineering.rag import tools

    monkeypatch.setattr(tools, "check_policy_compliance", lambda app: {"results": []})


def _verdict(app=None, financial=None, transactions=None):
    """Run the real evaluator on a clean applicant with the given overrides, then the decision."""
    application = {"age": 40, "declared_monthly_net_income": 5000, "employment_length_months": 24,
                   "credit_score": 700, "bankruptcies_count": 0, "tax_liens_count": 0, "dependents_count": 0,
                   **(app or {})}
    fin = {"dti_pct": 20.0, "lti_ratio": 0.2, "ndi_amount": 2000.0, "income_variance_pct": 0.0, **(financial or {})}
    txn = {"gambling_pct_of_income": 0.0, "nsf_event_count": 0, "undisclosed_debt_total": 0.0,
           "window_dressing_events": [], "burn_rate_status": "HEALTHY", **(transactions or {})}
    policy = evaluate_policies({"application": application}, fin, txn)["data"]
    return _decision(policy, fin, txn, application), policy


def test_clean_applicant_is_eligible():
    assert _verdict()[0] == ELIGIBLE


SCORE = [(599, DECLINE), (600, REVIEW), (659, REVIEW), (660, ELIGIBLE)]
DTI = [(35, ELIGIBLE), (35.1, REVIEW), (43, REVIEW), (50, REVIEW), (50.1, DECLINE)]
VARIANCE = [(10, ELIGIBLE), (10.1, REVIEW), (25, REVIEW), (25.1, DECLINE)]
NSF = [(0, ELIGIBLE), (1, REVIEW), (2, REVIEW), (3, REVIEW), (4, DECLINE)]
GAMBLING = [(0, ELIGIBLE), (2.9, ELIGIBLE), (3, REVIEW), (10, REVIEW), (10.1, DECLINE)]


@pytest.mark.parametrize("score,expected", SCORE)
def test_credit_score_boundaries(score, expected):
    assert _verdict(app={"credit_score": score})[0] == expected


@pytest.mark.parametrize("dti,expected", DTI)
def test_dti_boundaries(dti, expected):
    assert _verdict(financial={"dti_pct": dti})[0] == expected


@pytest.mark.parametrize("variance,expected", VARIANCE)
def test_income_variance_boundaries(variance, expected):
    assert _verdict(financial={"income_variance_pct": variance})[0] == expected


@pytest.mark.parametrize("nsf,expected", NSF)
def test_nsf_boundaries(nsf, expected):
    assert _verdict(transactions={"nsf_event_count": nsf})[0] == expected


@pytest.mark.parametrize("pct,expected", GAMBLING)
def test_gambling_boundaries(pct, expected):
    assert _verdict(transactions={"gambling_pct_of_income": pct})[0] == expected


@pytest.mark.parametrize("app,financial,transactions,expected", [
    ({"bankruptcies_count": 1}, None, None, DECLINE),
    ({"tax_liens_count": 1}, None, None, DECLINE),
    ({"employment_length_months": 5}, None, None, REVIEW),          # job under 6 months
    ({"employment_length_months": 0}, None, None, REVIEW),          # NOT_SATISFIED but not in the matrix
    ({"age": 19}, None, None, REVIEW),                              # eligibility failure: human decides
    ({"declared_monthly_net_income": 1500}, None, None, REVIEW),
    (None, {"ndi_amount": -1.0}, None, REVIEW),                     # negative NDI: not in the matrix
    (None, None, {"undisclosed_debt_total": 50.0}, REVIEW),         # any undisclosed debt
    (None, None, {"undisclosed_debt_total": 740.0}, REVIEW),        # over $250: still a human call
    (None, None, {"window_dressing_events": [{"amount": 9000}]}, REVIEW),
    (None, None, {"burn_rate_status": "VULNERABLE"}, REVIEW),
    ({"credit_score": 590}, {"dti_pct": 40}, {"nsf_event_count": 2}, DECLINE),  # a knockout beats referrals
])
def test_other_matrix_cases(app, financial, transactions, expected):
    assert _verdict(app, financial, transactions)[0] == expected


def test_missing_data_does_not_change_verdict():
    assert _verdict(financial={"ndi_amount": None, "lti_ratio": None})[0] == ELIGIBLE
    assert _verdict(financial={"income_variance_pct": None})[0] == ELIGIBLE


def test_empty_policy_result_is_never_approved():
    assert _classify({}) == (REVIEW, "Policy evaluation unavailable")


def test_primary_driver_names_the_deciding_rule():
    assert _classify({"POL-DTI-001": "FLAG_FOR_REVIEW", "POL-TXN-002": "KNOCKOUT"}) == (DECLINE, "POL-TXN-002")
    assert _classify({"POL-ELG-001": "SATISFIED", "POL-SCR-001": "Tier 3"}) == (REVIEW, "POL-SCR-001")
    assert _classify({"POL-ELG-001": "SATISFIED", "POL-SCR-001": "Tier 1"})[0] == ELIGIBLE


@pytest.mark.parametrize("policy,verdict,driver", [
    # NOT_SATISFIED outranks review-class labels even when it comes later in rule order
    ({"POL-NDI-001": "FLAG_FOR_REVIEW", "POL-TXN-003": "NOT_SATISFIED"}, REVIEW, "POL-TXN-003"),
    ({"POL-ELG-003": "FLAG_FOR_REVIEW", "POL-DTI-001": "CONDITIONAL", "POL-TXN-002": "CAUTION"}, REVIEW, "POL-ELG-003"),
    ({"POL-DTI-001": "CONDITIONAL", "POL-INC-001": "REVIEW_REQUIRED"}, REVIEW, "POL-DTI-001"),  # tie: rule order
    ({"POL-TXN-001": "FLAG_FOR_REVIEW", "POL-ELG-002": "NOT_SATISFIED", "POL-NDI-001": "NOT_SATISFIED"}, REVIEW, "POL-ELG-002"),
    ({"POL-SCR-001": "Tier 3", "POL-TXN-005": "CRITICAL_DISTRESS"}, REVIEW, "POL-TXN-005"),
    # a decline-class rule outranks everything, wherever it sits
    ({"POL-ELG-001": "NOT_SATISFIED", "POL-TXN-002": "KNOCKOUT"}, DECLINE, "POL-TXN-002"),
    ({"POL-DTI-001": "NOT_SATISFIED", "POL-INC-001": "HIGH_RISK"}, DECLINE, "POL-DTI-001"),  # tie: rule order
])
def test_primary_driver_is_the_most_severe_rule(policy, verdict, driver):
    assert _classify(policy) == (verdict, driver)


def test_undisclosed_debt_persona_driver_is_the_undisclosed_debt_rule():
    from ai_engineering.demo.cases import find_case, load_cases, load_transactions, run_case

    case = find_case(load_cases(), "CUST-GOLD-004")
    _, result = run_case(case, load_transactions())
    decision = result["report"]["final_decision"]
    assert result["report"]["policy_assessment"]["POL-NDI-001"] == "FLAG_FOR_REVIEW"  # still flagged, but less severe
    assert decision == {"verdict": REVIEW, "primary_driver": "POL-TXN-003"}


# ----------------------------------------------------------------------------- NDI (POL-NDI-001)


@pytest.mark.parametrize("dependents,buffer", [(0, 500), (1, 800), (2, 1000), (3, 1200)])
def test_ndi_buffer_as_written(dependents, buffer):
    assert ndi_buffer(dependents) == buffer


@pytest.mark.parametrize("ndi,dependents,expected", [
    (-0.01, 0, "NOT_SATISFIED"), (0, 0, "FLAG_FOR_REVIEW"), (499.99, 0, "FLAG_FOR_REVIEW"), (500, 0, "SATISFIED"),
    (799.99, 1, "FLAG_FOR_REVIEW"), (800, 1, "SATISFIED"),
    (999, 2, "FLAG_FOR_REVIEW"), (1000, 2, "SATISFIED"),
    (None, 0, "MISSING_DATA"), (900, None, "MISSING_DATA"),
])
def test_ndi_status(ndi, dependents, expected):
    assert ndi_status(ndi, dependents) == expected


def test_ndi_missing_without_living_expenses_and_computed_with():
    from ai_engineering.financial_analysis.income_expense_analysis import net_disposable_income

    app = {"declared_monthly_net_income": 5000, "declared_monthly_housing_expense": 1400,
           "declared_existing_monthly_debt": 450}
    assert net_disposable_income(app, 466.59) is None  # no default is invented
    assert net_disposable_income({**app, "declared_monthly_living_expenses": 1500}, 466.59) == pytest.approx(1183.41)


# ----------------------------------------------------------------------------- data gaps vs failures

_CASE = {"application": {"age": 40, "declared_monthly_net_income": 5000, "employment_length_months": 24,
                         "credit_score": 700, "declared_annual_income": 60000, "requested_loan_amount": 10000,
                         "loan_term_months": 36, "interest_rate_pct": 8, "declared_existing_monthly_debt": 300,
                         "declared_monthly_housing_expense": 1200, "dependents_count": 0}, "transactions": []}


def test_missing_data_is_a_gap_not_a_failure():
    result = investigate(_CASE)
    gaps = {g["rule"]: g["missing_fields"] for g in result["report"]["data_gaps"]}
    assert "declared_monthly_living_expenses" in gaps["POL-NDI-001"]
    assert result["system"]["status"] == "ok"
    assert result["system"]["modules_failed"] == []


def test_complete_data_has_no_gap_for_ndi():
    case = {**_CASE, "application": {**_CASE["application"], "declared_monthly_living_expenses": 1500}}
    gaps = {g["rule"] for g in investigate(case)["report"]["data_gaps"]}
    assert "POL-NDI-001" not in gaps


def test_real_module_failure_marks_fallback(monkeypatch):
    failing = module_result("anomaly_detection", {}, [], [log_error("analysis_failure", "boom", "anomaly_detection")], "fallback")
    monkeypatch.setattr(orchestrator, "analyse_anomalies", lambda data, txn: failing)
    result = investigate(_CASE)
    assert result["system"]["status"] == "fallback"
    assert result["system"]["modules_failed"] == ["anomaly_detection"]


def test_find_data_gaps_names_fields():
    gaps = find_data_gaps({"application": {}}, {}, {}, {"POL-ELG-001": "MISSING_DATA", "POL-DTI-001": "SATISFIED"})
    assert gaps == [{"rule": "POL-ELG-001", "missing_fields": ["age"]}]
