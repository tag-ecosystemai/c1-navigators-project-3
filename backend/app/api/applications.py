from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.application import CreditApplicationCreate,CreditApplicationResponse
from app.services.application_service import create_application,get_application,to_response
router=APIRouter()
@router.post('',response_model=CreditApplicationResponse,status_code=201)
def create(data:CreditApplicationCreate,db:Session=Depends(get_db)): return create_application(db,data)
@router.get('/{application_id}',response_model=CreditApplicationResponse)
def get(application_id:str,db:Session=Depends(get_db)):
 x=get_application(db,application_id)
 if not x: raise HTTPException(404,'Application not found')
 return to_response(x)
