from app.schemas.ai_results import FinancialAnalysisResult
class FinancialAnalysisInterface:
 async def analyze(self,d):
  income=d.get('annual_income',0); assets=d.get('total_assets',0)
  return FinancialAnalysisResult(ratios={'expense_to_income':round(d.get('annual_expenses',0)/income,4) if income else 0,'debt_to_asset':round(d.get('total_liabilities',0)/assets,4) if assets else 0},findings=['Mock financial analysis completed.'])
financial_analysis=FinancialAnalysisInterface()
