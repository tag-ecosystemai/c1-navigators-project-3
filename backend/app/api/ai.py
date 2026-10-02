from fastapi import APIRouter
from app.integrations.policy_rag import policy_rag
from app.integrations.financial_analysis import financial_analysis
from app.integrations.transaction_analysis import transaction_analysis
from app.integrations.anomaly_detection import anomaly_detection
from app.integrations.credit_risk_model import credit_risk_model
router=APIRouter()
@router.post('/policy-analysis')
async def policy(data:dict): return await policy_rag.analyze_application(data)
@router.post('/financial-analysis')
async def financial(data:dict): return await financial_analysis.analyze(data)
@router.post('/transaction-analysis')
async def transaction(data:list[dict]): return await transaction_analysis.analyze(data)
@router.post('/anomaly-detection')
async def anomaly(data:list[dict]): return await anomaly_detection.detect(data)
@router.post('/credit-risk')
async def risk(data:dict): return await credit_risk_model.predict(data)
