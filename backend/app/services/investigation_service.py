from datetime import datetime,timezone
from sqlalchemy.orm import Session
from app.db.models import Investigation,Report
from app.integrations.policy_rag import policy_rag
from app.integrations.financial_analysis import financial_analysis
from app.integrations.transaction_analysis import transaction_analysis
from app.integrations.anomaly_detection import anomaly_detection
from app.integrations.credit_risk_model import credit_risk_model
from app.integrations.report_generator import report_generator
from app.services.application_service import get_application
from app.services.case_service import get_case
from app.services.evidence_service import synthesize_evidence
from app.schemas.investigation import InvestigationResponse
def resp(x): return InvestigationResponse(investigation_id=x.id,case_id=x.case_id,status=x.status,started_at=x.started_at,completed_at=x.completed_at,error=x.error)
async def run_investigation(db:Session,case_id:str):
    case=get_case(db,case_id)
    if not case: raise ValueError('Case not found')
    app=get_application(db,case.application_id)
    inv=Investigation(case_id=case_id,status='running',started_at=datetime.now(timezone.utc)); db.add(inv); case.status='investigating'; db.commit(); db.refresh(inv)
    try:
        data={'application_id':app.id,'applicant_name':app.applicant_name,'requested_amount':app.requested_amount,'loan_purpose':app.loan_purpose,'employment_status':app.employment_status,'credit_score':app.credit_score,'financial_data':app.financial_data,'transactions':app.transactions}
        policy=await policy_rag.analyze_application(data); financial=await financial_analysis.analyze(app.financial_data); transaction=await transaction_analysis.analyze(app.transactions); anomaly=await anomaly_detection.detect(app.transactions)
        risk=await credit_risk_model.predict({'application':data,'financial':financial.model_dump(),'transaction':transaction.model_dump(),'anomaly':anomaly.model_dump()})
        evidence=synthesize_evidence(policy,financial,transaction,anomaly,risk); report=await report_generator.generate(case_id,evidence)
        db.add(Report(id=report.report_id,case_id=case_id,title=report.title,summary=report.summary,key_findings=report.key_findings,risk_factors=report.risk_factors,supporting_evidence=report.supporting_evidence,risk_score=report.risk_score,risk_category=report.risk_category,generated_at=report.generated_at))
        inv.status='completed'; inv.completed_at=datetime.now(timezone.utc); case.status='completed'; db.commit(); db.refresh(inv); return resp(inv)
    except Exception as e:
        inv.status='failed'; inv.error=str(e); case.status='open'; db.commit(); raise

def latest(db,case_id): return db.query(Investigation).filter(Investigation.case_id==case_id).order_by(Investigation.started_at.desc()).first()
def get(db,id): return db.get(Investigation,id)
