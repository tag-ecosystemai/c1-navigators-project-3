from datetime import datetime
from pydantic import BaseModel
class ReportResponse(BaseModel):
    report_id:str; case_id:str; title:str; summary:str; key_findings:list[str]=[]; risk_factors:list[str]=[]; supporting_evidence:list[dict]=[]; risk_score:float|None=None; risk_category:str|None=None; generated_at:datetime; status:str='generated'
