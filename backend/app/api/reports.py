from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Report
from app.schemas.report import ReportResponse
router=APIRouter()
@router.get('/{case_id}',response_model=ReportResponse)
def get(case_id:str,db:Session=Depends(get_db)):
 x=db.query(Report).filter(Report.case_id==case_id).order_by(Report.generated_at.desc()).first()
 if not x: raise HTTPException(404,'Report not found')
 return ReportResponse(report_id=x.id,case_id=x.case_id,title=x.title,summary=x.summary,key_findings=x.key_findings,risk_factors=x.risk_factors,supporting_evidence=x.supporting_evidence,risk_score=x.risk_score,risk_category=x.risk_category,generated_at=x.generated_at)
