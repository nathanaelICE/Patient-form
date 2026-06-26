from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime
import re


VALID_GENDERS = {"male", "female", "other"}
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")


class PatientCreate(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('must not be blank')
        return v.strip()

    @field_validator('gender')
    @classmethod
    def gender_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('must not be blank')
        normalized = v.strip().lower()
        if normalized not in VALID_GENDERS:
            raise ValueError(f"must be one of: {', '.join(sorted(VALID_GENDERS))}")
        return normalized

    @field_validator('date_of_birth')
    @classmethod
    def dob_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError('date of birth cannot be in the future')
        return v

    @field_validator('phone')
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not PHONE_RE.match(v):
            raise ValueError('phone number format is invalid')
        return v


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str]
    created_at: datetime


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('must not be blank')
            return v.strip()
        return v

    @field_validator('gender')
    @classmethod
    def gender_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            normalized = v.strip().lower()
            if normalized not in VALID_GENDERS:
                raise ValueError(f"must be one of: {', '.join(sorted(VALID_GENDERS))}")
            return normalized
        return v

    @field_validator('date_of_birth')
    @classmethod
    def dob_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError('date of birth cannot be in the future')
        return v

    @field_validator('phone')
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not PHONE_RE.match(v):
            raise ValueError('phone number format is invalid')
        return v


class VisitCreate(BaseModel):
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('chief_complaint')
    @classmethod
    def complaint_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('must not be blank')
        return v.strip()

    @field_validator('diagnosis', 'notes')
    @classmethod
    def optional_str_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    date: date
    chief_complaint: str
    diagnosis: Optional[str]
    notes: Optional[str]
    created_at: datetime


class VisitUpdate(BaseModel):
    date: Optional[date] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('chief_complaint')
    @classmethod
    def complaint_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('must not be blank')
            return v.strip()
        return v

    @field_validator('diagnosis', 'notes')
    @classmethod
    def optional_str_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator('username', 'password')
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('must not be blank')
        return v


class MeResponse(BaseModel):
    is_admin: bool
