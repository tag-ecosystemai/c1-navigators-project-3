from sqlalchemy.orm import Session
from app.db.models import Application
from app.schemas.application import CreditApplicationCreate, CreditApplicationResponse
def create_application(db:Session,data:CreditApplicationCreate):
    x=Application(applicant_name=data.applicant_name,requested_amount=data.requested_amount,loan_purpose=data.loan_purpose,employment_status=data.employment_status,credit_score=data.credit_score,financial_data=data.financial_data.model_dump(),transactions=[t.model_dump(mode='json') for t in data.transactions]); db.add(x); db.commit(); db.refresh(x); return to_response(x)
def get_application(db,id): return db.get(Application,id)
def to_response(x): return CreditApplicationResponse(application_id=x.id,applicant_name=x.applicant_name,requested_amount=x.requested_amount,loan_purpose=x.loan_purpose,employment_status=x.employment_status,credit_score=x.credit_score,financial_data=x.financial_data,transactions=x.transactions,created_at=x.created_at)
