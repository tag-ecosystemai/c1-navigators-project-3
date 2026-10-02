from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.case import CaseCreate,CaseResponse
from app.services.application_service import get_application
from app.services.case_service import create_case,get_case,to_response
router=APIRouter()
@router.post('',response_model=CaseResponse,status_code=201)
def create(data:CaseCreate,db:Session=Depends(get_db)):
 if not get_application(db,data.application_id): raise HTTPException(404,'Application not found')
 return create_case(db,data)
@router.get('/{case_id}',response_model=CaseResponse)
def get(case_id:str,db:Session=Depends(get_db)):
 x=get_case(db,case_id)
 if not x: raise HTTPException(404,'Case not found')
 return to_response(x)
