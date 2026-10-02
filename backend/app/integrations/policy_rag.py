from app.schemas.ai_results import PolicyAnalysisResult
class PolicyRAGInterface:
 async def analyze_application(self,application_data): return PolicyAnalysisResult(compliant=True,policy_findings=['Mock policy analysis completed.'])
policy_rag=PolicyRAGInterface()
