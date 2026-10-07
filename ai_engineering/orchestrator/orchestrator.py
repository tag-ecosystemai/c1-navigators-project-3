from ..utils.validation import validate_input
from ..utils.error_handler import log_error
from ..utils.evidence_builder import sort_evidence
from ..utils.time_utils import iso_timestamp
from ..financial_analysis.financial_summary import analyse_financials
from ..transaction_analysis.transaction_metrics import analyse_transactions
from ..financial_analysis.ratio_analysis import dti
from ..anomaly_detection.anomaly_scoring import analyse_anomalies
from ..policy_engine.policy_evaluator import evaluate_policies, find_data_gaps
from ..ml_scoring.feature_builder import feature_result
from ..ml_scoring.ml_integration import integrate_ml
from ..rag.cross_check import run_cross_check


# Decision matrix from data/policies/04_underwriting_referral_and_exception_matrix.md.
#
# Knockouts (matrix section 3, "Recommended for Decline"), as the evaluator's labels:
#   score < 600 -> POL-SCR-001 "Tier 4";  DTI > 50 -> POL-DTI-001 NOT_SATISFIED;
#   >= 4 NSF -> POL-TXN-002 KNOCKOUT;     income variance > 25 -> POL-INC-001 HIGH_RISK;
#   active bankruptcy / tax lien -> POL-SCR-002 NOT_SATISFIED;
#   gambling > 10% -> POL-TXN-001 NOT_SATISFIED.
_KNOCKOUTS = {
    "POL-SCR-001": {"Tier 4"},
    "POL-DTI-001": {"NOT_SATISFIED"},
    "POL-TXN-002": {"KNOCKOUT"},
    "POL-INC-001": {"HIGH_RISK"},
    "POL-SCR-002": {"NOT_SATISFIED"},
    "POL-TXN-001": {"NOT_SATISFIED"},
}
# States that satisfy the "Standard Approval" criteria (score >= 660 = Tier 1/2, DTI <= 35, 0 NSF,
# gambling < 3%, no undisclosed debt, income variance <= 10). MISSING_DATA is deliberately neutral
# here: it is reported through report["data_gaps"] and does not change the verdict.
_PASSING = {"SATISFIED", "CLEAN", "HEALTHY", "Tier 1", "Tier 2", "MISSING_DATA"}


def _classify(policy):
    """Return (verdict, primary_driver) for a dict of {rule code: evaluator label}."""
    for code, bad in _KNOCKOUTS.items():
        if policy.get(code) in bad:
            return "DECLINE_RECOMMENDED", code

    # Everything that is not a knockout and not a clean pass goes to a person. That covers the
    # matrix's referral list (Tier 3, DTI 35.1-50, variance 10.1-25, 1-3 NSF, gambling 3-10%,
    # undisclosed debt, job < 6 months) and also NOT_SATISFIED rules the matrix gives no verdict
    # for (eligibility failures, negative NDI, undisclosed debt over $250). The policy does not
    # say decline for those, so a human decides rather than the engine guessing.
    for code, value in policy.items():
        if value not in _PASSING:
            return "FURTHER_REVIEW_REQUIRED", code

    if not policy:  # the evaluator produced nothing: never approve on an empty policy result
        return "FURTHER_REVIEW_REQUIRED", "Policy evaluation unavailable"
    return "ELIGIBLE_FOR_APPROVAL", "All policy checks satisfied"


def _decision(policy, financial, transactions, application):
    return _classify(policy)[0]


def _module_failed(module):
    # Missing input data is a finding for the analyst (see data_gaps), not a failure. A module
    # only counts as failed when it reported some other kind of error.
    return any(error["category"] != "missing_data" for error in module["errors"])


def investigate(case_input):
    data, errors = validate_input(case_input)
    modules = []

    financial = analyse_financials(data)
    modules.append(financial)

    transactions = analyse_transactions(data)
    modules.append(transactions)

    financial["data"]["shadow_dti_pct"] = dti(
        data["application"],
        financial["data"].get("proposed_monthly_payment"),
        transactions["data"].get("undisclosed_debt_total", 0.0)
    )

    anomalies = analyse_anomalies(data, transactions["data"])
    modules.append(anomalies)

    policy = evaluate_policies(data, financial["data"], transactions["data"])
    modules.append(policy)

    policy_check = run_cross_check({**data["application"], **financial["data"], **transactions["data"]}, policy["data"])

    features = feature_result(
        data, financial["data"], transactions["data"], anomalies["data"]
    )
    modules.append(features)

    ml = integrate_ml(data, features["data"])
    modules.append(ml)

    verdict = _decision(
        policy["data"], financial["data"], transactions["data"], data["application"]
    )

    driver = _classify(policy["data"])[1]

    data_gaps = find_data_gaps(data, financial["data"], transactions["data"], policy["data"])

    all_errors = errors + [error for module in modules for error in module["errors"]]
    evidence = sort_evidence([item for module in modules for item in module["evidence"]])

    failed_modules = [module for module in modules if _module_failed(module)]
    degraded = any(error["category"] != "missing_data" for error in errors) or bool(failed_modules)

    report = {
        "summary": "Degraded analysis used fallback values." if degraded else "Investigation completed.",
        "data_gaps": data_gaps,
        "financial_assessment": financial["data"],
        "transaction_assessment": transactions["data"],
        "anomaly_assessment": anomalies["data"],
        "policy_assessment": policy["data"],
        "policy_cross_check": policy_check,
        "risk_assessment": ml["data"],
        "final_decision": {
            "verdict": verdict,
            "primary_driver": driver
        }
    }

    return {
        "report": report,
        "evidence": evidence,
        "ml": ml["data"],
        "system": {
            "status": "fallback" if degraded else "ok",
            "errors": sorted(all_errors, key=lambda error: error["timestamp"]),
            "modules_executed": [module["module"] for module in modules],
            "modules_failed": [module["module"] for module in failed_modules],
            "timestamp": iso_timestamp()
        }
    }


if __name__ == "__main__":
    import json
    from ai_engineering.orchestrator.llm_client import LLMClient
    from ai_engineering.orchestrator.agents import LLMExplanationAgent


    # Load a sample synthetic applicant
    with open("data/processed/applications.json", "r") as f:
        applicants = json.load(f)

    sample = applicants[0]

    case_input = {
        "application": sample,
        "transactions": sample.get("transactions", [])
    }

    # Run core engine
    result = investigate(case_input)

    # Real LLM explanation
    llm = LLMClient()  # Azure OpenAI, configured from .env
    llm_agent = LLMExplanationAgent(llm_client=llm)

    explanation = llm_agent.explain(
        report=result["report"],
        evidence=result["evidence"],
        system=result["system"]
    )

    result["explanation"] = explanation

    print(json.dumps(result, indent=2))
