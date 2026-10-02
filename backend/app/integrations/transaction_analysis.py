from app.schemas.ai_results import TransactionAnalysisResult
class TransactionAnalysisInterface:
 async def analyze(self,tx):
  return TransactionAnalysisResult(transaction_count=len(tx),total_inflow=sum(x['amount'] for x in tx if x.get('transaction_type','').lower()=='inflow'),total_outflow=sum(x['amount'] for x in tx if x.get('transaction_type','').lower()=='outflow'),findings=['Mock transaction analysis completed.'])
transaction_analysis=TransactionAnalysisInterface()
