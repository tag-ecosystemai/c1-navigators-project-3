from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.investigation import InvestigationResponse
from app.services.investigation_service import run_investigation,latest,get,resp
router=APIRouter()
@router.post('/{case_id}/run',response_model=InvestigationResponse)
async def run(case_id:str,db:Session=Depends(get_db)):
 try: return await run_investigation(db,case_id)
 except ValueError as e: raise HTTPException(404,str(e))
@router.get('/{case_id}',response_model=InvestigationResponse)
def latest_investigation(case_id:str,db:Session=Depends(get_db)):
 x=latest(db,case_id)
 if not x: raise HTTPException(404,'Investigation not found')
 return resp(x)
@router.get('/detail/{investigation_id}',response_model=InvestigationResponse)
def detail(investigation_id:str,db:Session=Depends(get_db)):
 x=get(db,investigation_id)
 if not x: raise HTTPException(404,'Investigation not found')
 return resp(x)
