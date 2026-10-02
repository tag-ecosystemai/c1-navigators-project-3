from sqlalchemy.orm import Session
from app.db.models import Case
from app.schemas.case import CaseCreate,CaseResponse
def create_case(db:Session,data:CaseCreate):
    x=Case(application_id=data.application_id,assigned_analyst=data.assigned_analyst); db.add(x); db.commit(); db.refresh(x); return to_response(x)
def get_case(db,id): return db.get(Case,id)
def to_response(x): return CaseResponse(case_id=x.id,application_id=x.application_id,assigned_analyst=x.assigned_analyst,status=x.status,created_at=x.created_at)
