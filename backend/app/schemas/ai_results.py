from pydantic import BaseModel, Field
class EvidenceItem(BaseModel): source:str; section:str|None=None; text:str
class PolicyAnalysisResult(BaseModel): compliant:bool; policy_findings:list[str]=Field(default_factory=list); risk_flags:list[str]=Field(default_factory=list); evidence:list[EvidenceItem]=Field(default_factory=list)
class FinancialAnalysisResult(BaseModel): ratios:dict[str,float]=Field(default_factory=dict); findings:list[str]=Field(default_factory=list); risk_flags:list[str]=Field(default_factory=list)
class TransactionAnalysisResult(BaseModel): transaction_count:int; total_inflow:float=0; total_outflow:float=0; findings:list[str]=Field(default_factory=list); risk_flags:list[str]=Field(default_factory=list)
class AnomalyDetectionResult(BaseModel): anomalies_detected:int=0; findings:list[str]=Field(default_factory=list); anomaly_ids:list[str]=Field(default_factory=list)
class CreditRiskResult(BaseModel): risk_score:float=Field(ge=0,le=1); risk_category:str; model_version:str
class EvidenceSynthesis(BaseModel): key_findings:list[str]=Field(default_factory=list); risk_factors:list[str]=Field(default_factory=list); evidence:list[EvidenceItem]=Field(default_factory=list); model_result:CreditRiskResult|None=None
