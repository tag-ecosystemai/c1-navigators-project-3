from datetime import datetime,timezone
from uuid import uuid4
from app.schemas.report import ReportResponse
class ReportGeneratorInterface:
 async def generate(self,case_id,evidence):
  m=evidence.model_result
  return ReportResponse(report_id=str(uuid4()),case_id=case_id,title='Credit Risk Investigation Report',summary='Mock report generated from investigation evidence.',key_findings=evidence.key_findings,risk_factors=evidence.risk_factors,supporting_evidence=[e.model_dump() for e in evidence.evidence],risk_score=m.risk_score if m else None,risk_category=m.risk_category if m else None,generated_at=datetime.now(timezone.utc))
report_generator=ReportGeneratorInterface()
