from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Visit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
