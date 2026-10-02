from datetime import datetime
from enum import Enum
from pydantic import BaseModel
class CaseStatus(str,Enum): OPEN='open'; INVESTIGATING='investigating'; COMPLETED='completed'; HUMAN_REVIEW='human_review'
class CaseCreate(BaseModel): application_id:str; assigned_analyst:str|None=None
class CaseResponse(BaseModel): case_id:str; application_id:str; assigned_analyst:str|None=None; status:CaseStatus; created_at:datetime
