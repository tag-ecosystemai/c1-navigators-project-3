from datetime import datetime
from pydantic import BaseModel, Field
class FinancialData(BaseModel):
    annual_income: float=Field(ge=0); annual_expenses: float=Field(ge=0); total_assets: float=Field(ge=0); total_liabilities: float=Field(ge=0)
class Transaction(BaseModel):
    transaction_id: str; date: datetime; amount: float; transaction_type: str; description: str|None=None
class CreditApplicationCreate(BaseModel):
    applicant_name: str; requested_amount: float=Field(gt=0); loan_purpose: str; employment_status: str; credit_score: float|None=Field(None,ge=0,le=850); financial_data: FinancialData; transactions: list[Transaction]=Field(default_factory=list)
class CreditApplicationResponse(CreditApplicationCreate):
    application_id: str; created_at: datetime
