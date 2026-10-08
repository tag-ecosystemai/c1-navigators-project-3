from ai_engineering.financial_analysis.financial_summary import analyse_financials
from ai_engineering.financial_analysis.ratio_analysis import dti
from ai_engineering.transaction_analysis.transaction_metrics import analyse_transactions
from ai_engineering.anomaly_detection.anomaly_scoring import analyse_anomalies
from ai_engineering.utils.validation import validate_input
from ai_engineering.utils.evidence_builder import sort_evidence
from ai_engineering.utils.time_utils import iso_timestamp
from ai_engineering.policy_engine.policy_evaluator import evaluate_policies, find_data_gaps
from ai_engineering.ml_scoring.feature_builder import feature_result
from ai_engineering.ml_scoring.ml_integration import integrate_ml
from ai_engineering.rag.cross_check import run_cross_check
# The decision logic lives in orchestrator.py and is reused here, not copied, so both paths always agree.
from ai_engineering.orchestrator.orchestrator import _classify, _decision, _module_failed


class DataAnalysisAgent:
    """
    Responsible for:
    - validating input
    - financial analysis
    - transaction analysis
    - anomaly detection
    - shadow DTI (DTI including undisclosed debt found in the transactions)
    """

    def run(self, case_input):
        # 1. Validate input (validate_input returns (data, errors))
        data, errors = validate_input(case_input)
        validation = {"data": data, "errors": errors}

        # 2. Financial analysis
        financial = analyse_financials(data)

        # 3. Transaction analysis
        transactions = analyse_transactions(data)

        financial["data"]["shadow_dti_pct"] = dti(
            data["application"],
            financial["data"].get("proposed_monthly_payment"),
            transactions["data"].get("undisclosed_debt_total", 0.0),
        )

        # 4. Anomaly detection
        anomalies = analyse_anomalies(data, transactions["data"])

        return {
            "validation": validation,
            "financial": financial,
            "transactions": transactions,
            "anomalies": anomalies,
        }


class ComplianceAgent:
    """
    Responsible for:
    - policy and compliance evaluation
    """

    def run(self, validation, financial, transactions):
        policies = evaluate_policies(
            validation["data"],
            financial["data"],
            transactions["data"],
        )
        return policies


class CreditRiskAgent:
    """
    Responsible for:
    - feature building
    - ML model scoring
    """

    def run(self, validation, financial, transactions, anomalies):
        features = feature_result(
            validation["data"],
            financial["data"],
            transactions["data"],
            anomalies["data"],
        )

        ml_result = integrate_ml(
            validation["data"],
            features["data"],
        )

        return {
            "features": features,
            "ml": ml_result,
        }


class LLMExplanationAgent:
    """
    Responsible for:
    - generating human-readable explanation using an LLM
    - does NOT change numeric decisions, only explains them
    """

    def __init__(self, llm_client=None):
        # llm_client could be a wrapper around GPT-4o, GPT-4 Turbo, etc.
        self.llm_client = llm_client

    def explain_view(self, view):
        """Explain a report view exactly as the demo does: written by the LLM from the report's facts when
        one is configured and its text passes the checks, otherwise the rule-based text.
        Returns {"text", "source", "label", "note"}."""
        from ai_engineering.demo.explain import explain

        return explain(view, self.llm_client)

    def explain(self, report, evidence, system):
        """
        Takes the structured report and evidence,
        returns a natural-language explanation.
        """
        if self.llm_client is None:
            return "Explanation agent not configured with an LLM."

        prompt = f"""
You are a credit risk underwriter.

Here is the structured investigation report:
{report}

Here is the evidence:
{evidence}

Here is the system status:
{system}

Explain the final decision in clear, human language.
Highlight:
- key risk drivers
- financial strengths/weaknesses
- policy impacts
- why the decision is appropriate.
"""

        explanation = self.llm_client.generate(prompt)
        return explanation


class OrchestratorAgent:
    """
    High-level agent that coordinates, in order:
    - DataAnalysisAgent
    - ComplianceAgent
    - CreditRiskAgent
    - LLMExplanationAgent

    run() returns the same structure as investigate() (report / evidence / ml / system), with the
    same final_decision {verdict, primary_driver}, plus "explanation" and "explanation_detail".
    """

    def __init__(self, llm_client=None):
        self.data_agent = DataAnalysisAgent()
        self.compliance_agent = ComplianceAgent()
        self.credit_agent = CreditRiskAgent()
        self.llm_agent = LLMExplanationAgent(llm_client=llm_client)

    def run(self, case_input):
        # 1. Data analysis
        data_result = self.data_agent.run(case_input)

        validation = data_result["validation"]
        financial = data_result["financial"]
        transactions = data_result["transactions"]
        anomalies = data_result["anomalies"]
        data = validation["data"]

        # 2. Compliance / policy (+ the RAG cross-check, which never fails the run)
        policies = self.compliance_agent.run(
            validation,
            financial,
            transactions,
        )
        policy_check = run_cross_check(
            {**data["application"], **financial["data"], **transactions["data"]}, policies["data"]
        )

        # 3. Credit risk (ML)
        credit_result = self.credit_agent.run(
            validation,
            financial,
            transactions,
            anomalies,
        )
        features = credit_result["features"]
        ml_result = credit_result["ml"]

        modules = [financial, transactions, anomalies, policies, features, ml_result]

        # 4. Decision: the same functions investigate() uses
        verdict = _decision(policies["data"], financial["data"], transactions["data"], data["application"])
        driver = _classify(policies["data"])[1]

        all_errors = validation["errors"] + [error for module in modules for error in module["errors"]]
        failed_modules = [module for module in modules if _module_failed(module)]
        degraded = any(error["category"] != "missing_data" for error in validation["errors"]) or bool(failed_modules)

        report = {
            "summary": "Degraded analysis used fallback values." if degraded else "Investigation completed.",
            "data_gaps": find_data_gaps(data, financial["data"], transactions["data"], policies["data"]),
            "financial_assessment": financial["data"],
            "transaction_assessment": transactions["data"],
            "anomaly_assessment": anomalies["data"],
            "policy_assessment": policies["data"],
            "policy_cross_check": policy_check,
            "risk_assessment": ml_result["data"],
            "final_decision": {
                "verdict": verdict,
                "primary_driver": driver,
            },
        }

        # 5. Evidence and system status, in investigate()'s shape
        result = {
            "report": report,
            "evidence": sort_evidence([item for module in modules for item in module["evidence"]]),
            "ml": ml_result["data"],
            "system": {
                "status": "fallback" if degraded else "ok",
                "errors": sorted(all_errors, key=lambda error: error["timestamp"]),
                "modules_executed": [module["module"] for module in modules],
                "modules_failed": [module["module"] for module in failed_modules],
                "timestamp": iso_timestamp(),
            },
        }

        # 6. Explanation: explains the decision, never changes it
        from ai_engineering.demo.view import build_view
        from ai_engineering.rag.mode import banner, is_azure_mode

        application = data["application"]
        view = build_view({"applicant_id": application.get("applicant_id", ""), "full_name": application.get("full_name", "")},
                          application, result, banner(), is_azure_mode())
        detail = self.llm_agent.explain_view(view)
        result["explanation"] = detail["text"]
        result["explanation_detail"] = {key: detail[key] for key in ("source", "label", "note")}
        return result
