print("Loaded agents.py from:", __file__)
from ai_engineering.financial_analysis.financial_summary import analyse_financials
from ai_engineering.transaction_analysis.transaction_metrics import analyse_transactions
from ai_engineering.anomaly_detection.anomaly_scoring import analyse_anomalies
from ai_engineering.utils.validation import validate_input
from ai_engineering.utils.time_utils import iso_timestamp
from ai_engineering.policy_engine.policy_evaluator import evaluate_policies
from ai_engineering.ml_scoring.feature_builder import feature_result
from ai_engineering.ml_scoring.ml_integration import integrate_ml

# If your imports are named slightly differently, adjust them to match your actual files.


class DataAnalysisAgent:
    """
    Responsible for:
    - validating input
    - financial analysis
    - transaction analysis
    - anomaly detection
    - DTI calculation (if you have a dti() function)
    """

    def run(self, case_input):
        # 1. Validate input
        validation = validate_input(case_input)

        # 2. Financial analysis
        financial = analyse_financials(validation["data"])

        # 3. Transaction analysis
        transactions = analyse_transactions(validation["data"])

        # 4. Anomaly detection
        anomalies = analyse_anomalies(validation["data"], transactions["data"])

        # If you have a DTI function, call it here and include in the result.

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

    def run(self, validation, financial, transactions, policies):
        features = feature_result(
            validation["data"],
            financial["data"],
            transactions["data"],
            policies["data"],
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
    High-level agent that coordinates:
    - DataAnalysisAgent
    - ComplianceAgent
    - CreditRiskAgent
    - LLMExplanationAgent
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

        # 2. Compliance / policy
        policies = self.compliance_agent.run(
            validation,
            financial,
            transactions,
        )

        # 3. Credit risk (ML)
        credit_result = self.credit_agent.run(
            validation,
            financial,
            transactions,
            policies,
        )

        ml_result = credit_result["ml"]

        # 4. Build report (you can mirror your existing investigate() structure here)
        report = {
            "final_decision": "TODO: plug in your existing decision logic here",
            "financial_assessment": financial["data"],
            "transaction_assessment": transactions["data"],
            "anomaly_assessment": anomalies["data"],
            "policy_assessment": policies["data"],
            "risk_assessment": ml_result["data"],
        }

        # 5. Evidence (you can reuse your existing evidence builder)
        evidence = {
            "validation": validation.get("evidence", []),
            "financial": financial.get("evidence", []),
            "transactions": transactions.get("evidence", []),
            "anomalies": anomalies.get("evidence", []),
            "policies": policies.get("evidence", []),
            "ml": ml_result.get("evidence", []),
        }

        system = {
            "status": "ok",
            "timestamp": iso_timestamp(),
        }

        # 6. LLM explanation
        explanation = self.llm_agent.explain(report, evidence, system)

        return {
            "report": report,
            "evidence": evidence,
            "system": system,
            "explanation": explanation,
        }
