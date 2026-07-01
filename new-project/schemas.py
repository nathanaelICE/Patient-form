from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime
import re


VALID_GENDERS = {"male", "female", "other"}
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")
VALID_EMPLOYMENT = {"employed", "unemployed", "retired", "student"}
VALID_CLAIM_STATUS = {"approved", "denied", "pending"}
VALID_CLAIM_TYPE = {"inpatient", "outpatient", "emergency", "routine"}
VALID_CLAIM_METHOD = {"online", "paper", "phone"}


def _normalize_optional_str(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    stripped = v.strip()
    return stripped if stripped else None


def _validate_choice(v, choices, label):
    v = _normalize_optional_str(v)
    if v is None:
        return None
    v = v.lower()
    if v not in choices:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(choices))}")
    return v


def _validate_nonnegative(v):
    if v is None:
        return None
    if v < 0:
        raise ValueError("must not be negative")
    return v


class PatientCreate(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    employment_status: Optional[str] = None
    income: Optional[float] = None

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

    @field_validator('employment_status')
    @classmethod
    def employment_status_valid(cls, v):
        return _validate_choice(v, VALID_EMPLOYMENT, "employment status")

    @field_validator('income')
    @classmethod
    def income_nonnegative(cls, v):
        return _validate_nonnegative(v)


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str]
    employment_status: Optional[str]
    income: Optional[float]
    created_at: datetime


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    employment_status: Optional[str] = None
    income: Optional[float] = None

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

    @field_validator('employment_status')
    @classmethod
    def employment_status_valid(cls, v):
        return _validate_choice(v, VALID_EMPLOYMENT, "employment status")

    @field_validator('income')
    @classmethod
    def income_nonnegative(cls, v):
        return _validate_nonnegative(v)


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


class ClaimCreate(BaseModel):
    claim_date: date
    claim_amount: float
    visit_id: Optional[int] = None
    diagnosis_code: Optional[str] = None
    procedure_code: Optional[str] = None
    claim_status: str = "pending"
    claim_type: str
    claim_submission_method: str
    provider_id: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_location: Optional[str] = None

    @field_validator('claim_amount')
    @classmethod
    def amount_nonnegative(cls, v):
        if v is None or v < 0:
            raise ValueError("must not be negative")
        return v

    @field_validator('claim_status')
    @classmethod
    def status_valid(cls, v):
        return _validate_choice(v, VALID_CLAIM_STATUS, "claim status")

    @field_validator('claim_type')
    @classmethod
    def type_valid(cls, v):
        result = _validate_choice(v, VALID_CLAIM_TYPE, "claim type")
        if result is None:
            raise ValueError("must not be blank")
        return result

    @field_validator('claim_submission_method')
    @classmethod
    def method_valid(cls, v):
        result = _validate_choice(v, VALID_CLAIM_METHOD, "claim submission method")
        if result is None:
            raise ValueError("must not be blank")
        return result

    @field_validator('diagnosis_code', 'procedure_code', 'provider_id',
                     'provider_specialty', 'provider_location')
    @classmethod
    def optional_strings_clean(cls, v):
        return _normalize_optional_str(v)


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    visit_id: Optional[int]
    claim_date: date
    claim_amount: float
    diagnosis_code: Optional[str]
    procedure_code: Optional[str]
    claim_status: str
    claim_type: str
    claim_submission_method: str
    provider_id: Optional[str]
    provider_specialty: Optional[str]
    provider_location: Optional[str]
    created_at: datetime


class ClaimUpdate(BaseModel):
    claim_date: Optional[date] = None
    claim_amount: Optional[float] = None
    visit_id: Optional[int] = None
    diagnosis_code: Optional[str] = None
    procedure_code: Optional[str] = None
    claim_status: Optional[str] = None
    claim_type: Optional[str] = None
    claim_submission_method: Optional[str] = None
    provider_id: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_location: Optional[str] = None

    @field_validator('claim_amount')
    @classmethod
    def amount_nonnegative(cls, v):
        return _validate_nonnegative(v)

    @field_validator('claim_status')
    @classmethod
    def status_valid(cls, v):
        return _validate_choice(v, VALID_CLAIM_STATUS, "claim status")

    @field_validator('claim_type')
    @classmethod
    def type_valid(cls, v):
        return _validate_choice(v, VALID_CLAIM_TYPE, "claim type")

    @field_validator('claim_submission_method')
    @classmethod
    def method_valid(cls, v):
        return _validate_choice(v, VALID_CLAIM_METHOD, "claim submission method")

    @field_validator('diagnosis_code', 'procedure_code', 'provider_id',
                     'provider_specialty', 'provider_location')
    @classmethod
    def optional_strings_clean(cls, v):
        return _normalize_optional_str(v)
