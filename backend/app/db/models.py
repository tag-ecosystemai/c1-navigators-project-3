from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def now(): return datetime.now(timezone.utc)
class Application(Base):
    __tablename__='applications'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=lambda:str(uuid4()))
    applicant_name: Mapped[str]=mapped_column(String(255), nullable=False)
    requested_amount: Mapped[float]=mapped_column(Float, nullable=False)
    loan_purpose: Mapped[str]=mapped_column(String(255), nullable=False)
    employment_status: Mapped[str]=mapped_column(String(100), nullable=False)
    credit_score: Mapped[float|None]=mapped_column(Float)
    financial_data: Mapped[dict]=mapped_column(JSON, default=dict)
    transactions: Mapped[list]=mapped_column(JSON, default=list)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    cases: Mapped[list['Case']]=relationship(back_populates='application', cascade='all, delete-orphan')
class Case(Base):
    __tablename__='cases'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=lambda:str(uuid4()))
    application_id: Mapped[str]=mapped_column(ForeignKey('applications.id'), nullable=False)
    assigned_analyst: Mapped[str|None]=mapped_column(String(255))
    status: Mapped[str]=mapped_column(String(50), default='open')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    application: Mapped['Application']=relationship(back_populates='cases')
    investigations: Mapped[list['Investigation']]=relationship(back_populates='case', cascade='all, delete-orphan')
    reports: Mapped[list['Report']]=relationship(back_populates='case', cascade='all, delete-orphan')
class Investigation(Base):
    __tablename__='investigations'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=lambda:str(uuid4()))
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'), nullable=False)
    status: Mapped[str]=mapped_column(String(50), default='not_started')
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    error: Mapped[str|None]=mapped_column(Text)
    case: Mapped['Case']=relationship(back_populates='investigations')
class Report(Base):
    __tablename__='reports'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=lambda:str(uuid4()))
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'), nullable=False)
    title: Mapped[str]=mapped_column(String(255))
    summary: Mapped[str]=mapped_column(Text)
    key_findings: Mapped[list]=mapped_column(JSON, default=list)
    risk_factors: Mapped[list]=mapped_column(JSON, default=list)
    supporting_evidence: Mapped[list]=mapped_column(JSON, default=list)
    risk_score: Mapped[float|None]=mapped_column(Float)
    risk_category: Mapped[str|None]=mapped_column(String(50))
    generated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    case: Mapped['Case']=relationship(back_populates='reports')
