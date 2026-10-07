from ..utils.validation import validate_input
from ..utils.error_handler import log_error
from ..utils.evidence_builder import sort_evidence
from ..utils.time_utils import iso_timestamp
from ..financial_analysis.financial_summary import analyse_financials
from ..transaction_analysis.transaction_metrics import analyse_transactions
from ..financial_analysis.ratio_analysis import dti
from ..anomaly_detection.anomaly_scoring import analyse_anomalies
from ..policy_engine.policy_evaluator import evaluate_policies
from ..ml_scoring.feature_builder import feature_result
from ..ml_scoring.ml_integration import integrate_ml
from ..rag.cross_check import run_cross_check


def _decision(policy, financial, transactions, application):
    decline = {"NOT_SATISFIED", "KNOCKOUT", "HIGH_RISK"}
    if any(value in decline for value in policy.values()):
        return "DECLINE_RECOMMENDED"

    review = {"FLAG_FOR_REVIEW", "CONDITIONAL", "REVIEW_REQUIRED",
              "CAUTION", "VULNERABLE", "CRITICAL_DISTRESS"}
    if any(value in review for value in policy.values()):
        return "FURTHER_REVIEW_REQUIRED"

    return "ELIGIBLE_FOR_APPROVAL"


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

    driver = next(
        (key for key, value in policy["data"].items()
         if value in {"NOT_SATISFIED", "KNOCKOUT", "HIGH_RISK", "FLAG_FOR_REVIEW"}),
        "All policy checks satisfied"
    )

    all_errors = errors + [error for module in modules for error in module["errors"]]
    evidence = sort_evidence([item for module in modules for item in module["evidence"]])

    degraded = bool(all_errors) or any(module["status"] == "fallback" for module in modules)

    report = {
        "summary": "Degraded analysis used fallback values." if degraded else "Investigation completed.",
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
            "modules_failed": [module["module"] for module in modules if module["status"] == "fallback"],
            "timestamp": iso_timestamp()
        }
    }


if __name__ == "__main__":
    import json
    import os
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
    api_key = os.environ.get("OPENAI_API_KEY")
    llm = LLMClient(api_key=api_key, model="gpt-4o")
    llm_agent = LLMExplanationAgent(llm_client=llm)

    explanation = llm_agent.explain(
        report=result["report"],
        evidence=result["evidence"],
        system=result["system"]
    )

    result["explanation"] = explanation

    print(json.dumps(result, indent=2))
