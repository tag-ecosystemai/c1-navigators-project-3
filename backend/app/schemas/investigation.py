from datetime import datetime
from enum import Enum
from pydantic import BaseModel
class InvestigationStatus(str,Enum): NOT_STARTED='not_started'; RUNNING='running'; COMPLETED='completed'; FAILED='failed'
class InvestigationResponse(BaseModel): investigation_id:str; case_id:str; status:InvestigationStatus; started_at:datetime|None=None; completed_at:datetime|None=None; error:str|None=None
