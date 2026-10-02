from app.schemas.ai_results import *
def synthesize_evidence(policy,financial,transaction,anomaly,risk):
    return EvidenceSynthesis(key_findings=policy.policy_findings+financial.findings+transaction.findings+anomaly.findings,risk_factors=policy.risk_flags+financial.risk_flags+transaction.risk_flags,evidence=policy.evidence,model_result=risk)
