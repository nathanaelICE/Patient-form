from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class PatientCreate(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str]
    created_at: datetime


class VisitCreate(BaseModel):
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    date: date
    chief_complaint: str
    diagnosis: Optional[str]
    notes: Optional[str]
    created_at: datetime
