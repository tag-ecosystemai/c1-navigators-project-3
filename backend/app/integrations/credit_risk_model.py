from app.schemas.ai_results import CreditRiskResult
class CreditRiskModelInterface:
 async def predict(self,features): return CreditRiskResult(risk_score=0.35,risk_category='medium',model_version='mock-v1')
credit_risk_model=CreditRiskModelInterface()
