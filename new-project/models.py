from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AdminUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    hashed_password: str


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    employment_status: Optional[str] = None
    income: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)


class Visit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    visit_id: Optional[int] = Field(default=None, foreign_key="visit.id")
    claim_date: date
    claim_amount: float
    diagnosis_code: Optional[str] = None
    procedure_code: Optional[str] = None
    claim_status: str = "pending"
    claim_type: str
    claim_submission_method: str
    provider_id: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
