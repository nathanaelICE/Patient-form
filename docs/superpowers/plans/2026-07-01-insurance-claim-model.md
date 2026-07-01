# Insurance Claim Data Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an insurance `Claim` entity plus two new `Patient` demographic fields, with full backend CRUD and a per-patient claims UI, so later "acceptance subspace" work has a schema to build on.

**Architecture:** A new normalized `Claim` table (patient-scoped, optional visit link, provider fields embedded) mirrors the existing `Visit` layering exactly — `models.py` (schema) / `schemas.py` (validation) / `routers/claims.py` (endpoints). The frontend adds a Claims section to the patient detail page reusing the visit React-Query + form patterns. No ML, no code validation, no global claims page.

**Tech Stack:** FastAPI, SQLModel (SQLite in tests / Postgres in prod), Pydantic v2, pytest; React + TypeScript, React Query, Vite, vitest.

## Global Constraints

- Backend layering is strict: DB schema in `models.py`, ALL validation in `schemas.py` (`field_validator`s), endpoints in `routers/`. Never put validation in models.
- Every patient-scoped query MUST filter `deleted_at is None` (patients are soft-deleted).
- New API routes must be registered in `main.py` **before** the SPA catch-all `/{full_path:path}`.
- Enum-like validation follows the existing `VALID_MARITAL` / `VALID_BLOOD` pattern: a `VALID_*` set + a validator that lowercases and checks membership.
- Optional strings use `_normalize_optional_str` (blank → `None`).
- Claims are hard-deleted (match `Visit`, not `Patient`).
- Route shape mirrors visits: `POST|GET /api/patients/{patient_id}/claims`, `PUT|DELETE /api/patients/{patient_id}/claims/{claim_id}`.
- Backend tests run with `uv run pytest` from `new-project/`; use the `admin_client` fixture for any endpoint behind `get_admin`.
- Frontend commands run from `new-project/frontend/`: `npm test`, `npm run build`.
- All paths below are relative to the repo's `new-project/` directory.

---

### Task 1: Add `Claim` model and new `Patient` fields

**Files:**
- Modify: `new-project/models.py`
- Modify: `new-project/database.py:16-18` (register `Claim` for table creation)

**Interfaces:**
- Produces: `Claim` SQLModel table class; `Patient.employment_status: Optional[str]`, `Patient.income: Optional[float]`. Column names later tasks rely on: `patient_id`, `visit_id`, `claim_date`, `claim_amount`, `diagnosis_code`, `procedure_code`, `claim_status`, `claim_type`, `claim_submission_method`, `provider_id`, `provider_specialty`, `provider_location`, `created_at`.

- [ ] **Step 1: Add the two new `Patient` fields**

In `new-project/models.py`, inside `class Patient`, after the `known_conditions` line and before `created_at`, add:

```python
    employment_status: Optional[str] = None
    income: Optional[float] = None
```

- [ ] **Step 2: Add the `Claim` table**

In `new-project/models.py`, after `class Visit`, add:

```python
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
```

- [ ] **Step 3: Register `Claim` for table creation**

In `new-project/database.py`, change line 17 from:

```python
    from models import Patient, Visit, AdminUser  # noqa: F401
```

to:

```python
    from models import Patient, Visit, Claim, AdminUser  # noqa: F401
```

- [ ] **Step 4: Verify the model imports cleanly**

Run: `cd new-project && uv run python -c "import models; print(models.Claim.__tablename__)"`
Expected: prints `claim` with no error.

- [ ] **Step 5: Commit**

```bash
git add new-project/models.py new-project/database.py
git commit -m "feat: add Claim model and patient employment/income fields"
```

---

### Task 2: Claim + Patient schemas with validation

**Files:**
- Modify: `new-project/schemas.py`
- Test: `new-project/tests/test_schemas_claims.py` (create)

**Interfaces:**
- Consumes: `Claim` column names from Task 1.
- Produces: `ClaimCreate`, `ClaimRead`, `ClaimUpdate` Pydantic models; `VALID_EMPLOYMENT`, `VALID_CLAIM_STATUS`, `VALID_CLAIM_TYPE`, `VALID_CLAIM_METHOD` sets; `employment_status`/`income` fields on `PatientCreate`/`PatientRead`/`PatientUpdate`.

- [ ] **Step 1: Write failing schema tests**

Create `new-project/tests/test_schemas_claims.py`:

```python
import pytest
from pydantic import ValidationError
from schemas import ClaimCreate, PatientCreate


def _valid_claim():
    return dict(
        claim_date="2026-06-01",
        claim_amount=1200.50,
        claim_type="outpatient",
        claim_submission_method="online",
    )


def test_claim_defaults_status_pending():
    c = ClaimCreate(**_valid_claim())
    assert c.claim_status == "pending"


def test_claim_lowercases_enums():
    c = ClaimCreate(**{**_valid_claim(), "claim_type": "Inpatient", "claim_submission_method": "PAPER"})
    assert c.claim_type == "inpatient"
    assert c.claim_submission_method == "paper"


def test_claim_rejects_bad_type():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_type": "spaceflight"})


def test_claim_rejects_bad_status():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_status": "maybe"})


def test_claim_rejects_negative_amount():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_amount": -5})


def test_claim_blank_codes_become_none():
    c = ClaimCreate(**{**_valid_claim(), "diagnosis_code": "  ", "provider_id": ""})
    assert c.diagnosis_code is None
    assert c.provider_id is None


def test_patient_employment_validated_and_income_nonnegative():
    p = PatientCreate(name="A", date_of_birth="2000-01-01", gender="male",
                      employment_status="Student", income=50000)
    assert p.employment_status == "student"
    with pytest.raises(ValidationError):
        PatientCreate(name="A", date_of_birth="2000-01-01", gender="male", income=-1)
    with pytest.raises(ValidationError):
        PatientCreate(name="A", date_of_birth="2000-01-01", gender="male",
                      employment_status="freelancer")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd new-project && uv run pytest tests/test_schemas_claims.py -v`
Expected: FAIL — `ImportError: cannot import name 'ClaimCreate'`.

- [ ] **Step 3: Add validation sets and helpers**

In `new-project/schemas.py`, after the existing `VALID_BLOOD` line (~line 10), add:

```python
VALID_EMPLOYMENT = {"employed", "unemployed", "retired", "student"}
VALID_CLAIM_STATUS = {"approved", "denied", "pending"}
VALID_CLAIM_TYPE = {"inpatient", "outpatient", "emergency", "routine"}
VALID_CLAIM_METHOD = {"online", "paper", "phone"}
```

After the existing `_validate_blood_type` function, add:

```python
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
```

- [ ] **Step 4: Add `employment_status`/`income` to the Patient schemas**

In `PatientCreate`, `PatientRead`, and `PatientUpdate`, add these two field declarations alongside the other optional fields:

```python
    employment_status: Optional[str] = None
    income: Optional[float] = None
```

In `PatientCreate` and `PatientUpdate` (both), add these validators:

```python
    @field_validator('employment_status')
    @classmethod
    def employment_status_valid(cls, v):
        return _validate_choice(v, VALID_EMPLOYMENT, "employment status")

    @field_validator('income')
    @classmethod
    def income_nonnegative(cls, v):
        return _validate_nonnegative(v)
```

- [ ] **Step 5: Add the Claim schemas**

At the end of `new-project/schemas.py`, add:

```python
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
        return _validate_choice(v, VALID_CLAIM_STATUS, "claim status") or "pending"

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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd new-project && uv run pytest tests/test_schemas_claims.py -v`
Expected: PASS (8 tests).

- [ ] **Step 7: Commit**

```bash
git add new-project/schemas.py new-project/tests/test_schemas_claims.py
git commit -m "feat: add Claim schemas and patient employment/income validation"
```

---

### Task 3: Claims router with CRUD endpoints

**Files:**
- Create: `new-project/routers/claims.py`
- Modify: `new-project/main.py:9` and `:42-44` (import + register router)
- Test: `new-project/tests/test_claims.py` (create)

**Interfaces:**
- Consumes: `ClaimCreate`/`ClaimRead`/`ClaimUpdate` (Task 2), `Claim`/`Patient` models (Task 1), `get_session`, `get_admin`.
- Produces: routes `POST|GET /api/patients/{patient_id}/claims`, `PUT|DELETE /api/patients/{patient_id}/claims/{claim_id}`.

- [ ] **Step 1: Write failing endpoint tests**

Create `new-project/tests/test_claims.py`:

```python
def _make_patient(admin_client):
    resp = admin_client.post("/api/patients", json={
        "name": "Jane", "date_of_birth": "1990-01-01", "gender": "female",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _claim_body(**over):
    body = {
        "claim_date": "2026-06-01",
        "claim_amount": 1200.5,
        "claim_type": "outpatient",
        "claim_submission_method": "online",
    }
    body.update(over)
    return body


def test_create_and_list_claim(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["patient_id"] == pid
    assert data["claim_status"] == "pending"
    assert data["claim_type"] == "outpatient"

    listed = admin_client.get(f"/api/patients/{pid}/claims")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_claim_rejects_bad_enum(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body(claim_type="nope"))
    assert resp.status_code == 422


def test_create_claim_rejects_negative_amount(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body(claim_amount=-1))
    assert resp.status_code == 422


def test_create_claim_missing_patient_404(admin_client):
    resp = admin_client.post("/api/patients/9999/claims", json=_claim_body())
    assert resp.status_code == 404


def test_update_claim(admin_client):
    pid = _make_patient(admin_client)
    cid = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body()).json()["id"]
    resp = admin_client.put(f"/api/patients/{pid}/claims/{cid}", json={"claim_status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["claim_status"] == "approved"


def test_delete_claim(admin_client):
    pid = _make_patient(admin_client)
    cid = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body()).json()["id"]
    assert admin_client.delete(f"/api/patients/{pid}/claims/{cid}").status_code == 204
    assert admin_client.get(f"/api/patients/{pid}/claims").json() == []


def test_claims_require_auth(client):
    resp = client.get("/api/patients/1/claims")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd new-project && uv run pytest tests/test_claims.py -v`
Expected: FAIL — 404s / route not found (router not registered yet).

- [ ] **Step 3: Create the claims router**

Create `new-project/routers/claims.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, Claim, AdminUser
from schemas import ClaimCreate, ClaimRead, ClaimUpdate

router = APIRouter(prefix="/api/patients", tags=["claims"])


def _get_live_patient(session: Session, patient_id: int) -> Patient:
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("/{patient_id}/claims", response_model=ClaimRead, status_code=201)
def create_claim(
    patient_id: int,
    claim_in: ClaimCreate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    claim = Claim(patient_id=patient_id, **claim_in.model_dump())
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


@router.get("/{patient_id}/claims", response_model=list[ClaimRead])
def list_claims(patient_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    _get_live_patient(session, patient_id)
    claims = session.exec(
        select(Claim).where(Claim.patient_id == patient_id).order_by(Claim.claim_date.desc())
    ).all()
    return claims


@router.put("/{patient_id}/claims/{claim_id}", response_model=ClaimRead)
def update_claim(
    patient_id: int,
    claim_id: int,
    claim_in: ClaimUpdate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    claim = session.get(Claim, claim_id)
    if not claim or claim.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Claim not found")
    data = claim_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(claim, field, value)
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


@router.delete("/{patient_id}/claims/{claim_id}", status_code=204)
def delete_claim(
    patient_id: int,
    claim_id: int,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    claim = session.get(Claim, claim_id)
    if not claim or claim.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Claim not found")
    session.delete(claim)
    session.commit()
```

- [ ] **Step 4: Register the router in `main.py`**

Change line 9 from:

```python
from routers import patients, visits, auth as auth_router
```

to:

```python
from routers import patients, visits, claims, auth as auth_router
```

After the `app.include_router(visits.router)` line (line 43), add:

```python
app.include_router(claims.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd new-project && uv run pytest tests/test_claims.py -v`
Expected: PASS (7 tests).

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `cd new-project && uv run pytest -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add new-project/routers/claims.py new-project/main.py new-project/tests/test_claims.py
git commit -m "feat: add claims CRUD endpoints"
```

---

### Task 4: Frontend claim API layer + types

**Files:**
- Modify: `new-project/frontend/src/api/types.ts`
- Create: `new-project/frontend/src/api/claims.ts`

**Interfaces:**
- Consumes: `apiFetch` from `./client`, backend routes from Task 3.
- Produces: TS types `Claim`, `ClaimCreate`, `ClaimUpdate`; hooks `useClaims`, `useCreateClaim`, `useUpdateClaim`, `useDeleteClaim`.

- [ ] **Step 1: Add claim types**

In `new-project/frontend/src/api/types.ts`, after the `VisitUpdate` type, add:

```typescript
export type ClaimStatus = 'approved' | 'denied' | 'pending'
export type ClaimType = 'inpatient' | 'outpatient' | 'emergency' | 'routine'
export type ClaimMethod = 'online' | 'paper' | 'phone'

export interface Claim {
  id: number
  patient_id: number
  visit_id: number | null
  claim_date: string
  claim_amount: number
  diagnosis_code: string | null
  procedure_code: string | null
  claim_status: ClaimStatus
  claim_type: ClaimType
  claim_submission_method: ClaimMethod
  provider_id: string | null
  provider_specialty: string | null
  provider_location: string | null
  created_at: string
}
export interface ClaimCreate {
  claim_date: string
  claim_amount: number
  visit_id?: number | null
  diagnosis_code?: string | null
  procedure_code?: string | null
  claim_status?: ClaimStatus
  claim_type: ClaimType
  claim_submission_method: ClaimMethod
  provider_id?: string | null
  provider_specialty?: string | null
  provider_location?: string | null
}
export type ClaimUpdate = Partial<ClaimCreate>
```

- [ ] **Step 2: Create the claims API hooks**

Create `new-project/frontend/src/api/claims.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { Claim, ClaimCreate, ClaimUpdate } from './types'

export function useClaims(patientId: number) {
  return useQuery({
    queryKey: ['claims', patientId],
    queryFn: () => apiFetch<Claim[]>(`/api/patients/${patientId}/claims`),
    enabled: Number.isFinite(patientId),
  })
}

export function useCreateClaim(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ClaimCreate) =>
      apiFetch<Claim>(`/api/patients/${patientId}/claims`, { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}

export function useUpdateClaim(patientId: number, claimId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ClaimUpdate) =>
      apiFetch<Claim>(`/api/patients/${patientId}/claims/${claimId}`, { method: 'PUT', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}

export function useDeleteClaim(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (claimId: number) =>
      apiFetch<void>(`/api/patients/${patientId}/claims/${claimId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}
```

- [ ] **Step 3: Type-check**

Run: `cd new-project/frontend && npm run build`
Expected: build succeeds (tsc passes). If pre-existing unrelated errors appear, confirm none reference `claims.ts`/`types.ts` claim additions.

- [ ] **Step 4: Commit**

```bash
git add new-project/frontend/src/api/types.ts new-project/frontend/src/api/claims.ts
git commit -m "feat(frontend): add claim api hooks and types"
```

---

### Task 5: ClaimForm component

**Files:**
- Create: `new-project/frontend/src/components/ClaimForm.tsx`
- Test: `new-project/frontend/src/components/ClaimForm.test.tsx` (create)

**Interfaces:**
- Consumes: `ClaimCreate` type, existing `FormField` component (read `new-project/frontend/src/components/FormField.tsx` and mirror `VisitForm.tsx`'s prop shape — `onSubmit: (body: ClaimCreate) => void`, `pending: boolean`, optional `fieldErrors: Record<string, string>`).
- Produces: default-exported `ClaimForm` React component.

- [ ] **Step 1: Read the existing VisitForm to mirror its structure**

Run: read `new-project/frontend/src/components/VisitForm.tsx` in full. The ClaimForm MUST follow the same prop names, controlled-input pattern, error display via `fieldErrors`, and submit handling.

- [ ] **Step 2: Write the failing test**

Create `new-project/frontend/src/components/ClaimForm.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../test-utils'
import ClaimForm from './ClaimForm'

describe('ClaimForm', () => {
  it('submits entered claim values', () => {
    const onSubmit = vi.fn()
    render(<ClaimForm onSubmit={onSubmit} pending={false} />)

    fireEvent.change(screen.getByLabelText(/claim date/i), { target: { value: '2026-06-01' } })
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '1200.5' } })
    fireEvent.change(screen.getByLabelText(/claim type/i), { target: { value: 'outpatient' } })
    fireEvent.change(screen.getByLabelText(/submission method/i), { target: { value: 'online' } })
    fireEvent.click(screen.getByRole('button', { name: /save|add|create/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        claim_date: '2026-06-01',
        claim_amount: 1200.5,
        claim_type: 'outpatient',
        claim_submission_method: 'online',
      })
    )
  })
})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd new-project/frontend && npm test -- ClaimForm`
Expected: FAIL — cannot find module `./ClaimForm`.

- [ ] **Step 4: Implement ClaimForm**

Create `new-project/frontend/src/components/ClaimForm.tsx`. Mirror `VisitForm.tsx`'s pattern exactly. Controlled state for every field; `claim_amount` parsed with `Number(...)`; `claim_status`/`claim_type`/`claim_submission_method` as `<select>` elements with the enum options; codes and provider fields as optional text inputs. Reference implementation:

```tsx
import { useState, FormEvent } from 'react'
import FormField from './FormField'
import type { ClaimCreate, ClaimStatus, ClaimType, ClaimMethod } from '../api/types'

interface Props {
  onSubmit: (body: ClaimCreate) => void
  pending: boolean
  fieldErrors?: Record<string, string>
}

const TYPES: ClaimType[] = ['inpatient', 'outpatient', 'emergency', 'routine']
const METHODS: ClaimMethod[] = ['online', 'paper', 'phone']
const STATUSES: ClaimStatus[] = ['pending', 'approved', 'denied']

export default function ClaimForm({ onSubmit, pending, fieldErrors = {} }: Props) {
  const [claimDate, setClaimDate] = useState('')
  const [amount, setAmount] = useState('')
  const [status, setStatus] = useState<ClaimStatus>('pending')
  const [type, setType] = useState<ClaimType>('outpatient')
  const [method, setMethod] = useState<ClaimMethod>('online')
  const [diagnosisCode, setDiagnosisCode] = useState('')
  const [procedureCode, setProcedureCode] = useState('')
  const [providerId, setProviderId] = useState('')
  const [providerSpecialty, setProviderSpecialty] = useState('')
  const [providerLocation, setProviderLocation] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      claim_date: claimDate,
      claim_amount: Number(amount),
      claim_status: status,
      claim_type: type,
      claim_submission_method: method,
      diagnosis_code: diagnosisCode || null,
      procedure_code: procedureCode || null,
      provider_id: providerId || null,
      provider_specialty: providerSpecialty || null,
      provider_location: providerLocation || null,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <FormField label="Claim date" htmlFor="claim_date" error={fieldErrors.claim_date}>
        <input id="claim_date" type="date" value={claimDate}
               onChange={(e) => setClaimDate(e.target.value)} required />
      </FormField>
      <FormField label="Amount (USD)" htmlFor="claim_amount" error={fieldErrors.claim_amount}>
        <input id="claim_amount" type="number" min="0" step="0.01" value={amount}
               onChange={(e) => setAmount(e.target.value)} required />
      </FormField>
      <FormField label="Claim type" htmlFor="claim_type" error={fieldErrors.claim_type}>
        <select id="claim_type" value={type} onChange={(e) => setType(e.target.value as ClaimType)}>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </FormField>
      <FormField label="Submission method" htmlFor="claim_submission_method"
                 error={fieldErrors.claim_submission_method}>
        <select id="claim_submission_method" value={method}
                onChange={(e) => setMethod(e.target.value as ClaimMethod)}>
          {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </FormField>
      <FormField label="Status" htmlFor="claim_status" error={fieldErrors.claim_status}>
        <select id="claim_status" value={status}
                onChange={(e) => setStatus(e.target.value as ClaimStatus)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </FormField>
      <FormField label="Diagnosis code" htmlFor="diagnosis_code" error={fieldErrors.diagnosis_code}>
        <input id="diagnosis_code" value={diagnosisCode}
               onChange={(e) => setDiagnosisCode(e.target.value)} />
      </FormField>
      <FormField label="Procedure code" htmlFor="procedure_code" error={fieldErrors.procedure_code}>
        <input id="procedure_code" value={procedureCode}
               onChange={(e) => setProcedureCode(e.target.value)} />
      </FormField>
      <FormField label="Provider ID" htmlFor="provider_id" error={fieldErrors.provider_id}>
        <input id="provider_id" value={providerId}
               onChange={(e) => setProviderId(e.target.value)} />
      </FormField>
      <FormField label="Provider specialty" htmlFor="provider_specialty"
                 error={fieldErrors.provider_specialty}>
        <input id="provider_specialty" value={providerSpecialty}
               onChange={(e) => setProviderSpecialty(e.target.value)} />
      </FormField>
      <FormField label="Provider location" htmlFor="provider_location"
                 error={fieldErrors.provider_location}>
        <input id="provider_location" value={providerLocation}
               onChange={(e) => setProviderLocation(e.target.value)} />
      </FormField>
      <button type="submit" disabled={pending}>Save claim</button>
    </form>
  )
}
```

Note: if `FormField`'s actual prop names differ (from Step 1), adjust to match — the test only depends on labels and the button.

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd new-project/frontend && npm test -- ClaimForm`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add new-project/frontend/src/components/ClaimForm.tsx new-project/frontend/src/components/ClaimForm.test.tsx
git commit -m "feat(frontend): add ClaimForm component"
```

---

### Task 6: Claims section on the patient detail page

**Files:**
- Modify: `new-project/frontend/src/pages/PatientDetailPage.tsx`
- Modify: `new-project/frontend/src/pages/PatientDetailPage.test.tsx`

**Interfaces:**
- Consumes: `useClaims`/`useCreateClaim`/`useDeleteClaim` (Task 4), `ClaimForm` (Task 5).
- Produces: a "Claims" section rendered on the patient detail page.

- [ ] **Step 1: Read the current detail page to locate the Visits section**

Run: read `new-project/frontend/src/pages/PatientDetailPage.tsx` in full. Identify how the Visits section is rendered (the `useVisits` list + `VisitForm` + create mutation + `ApiError.fieldErrors()` wiring). The Claims section mirrors it exactly.

- [ ] **Step 2: Write a failing test for the claims section**

In `new-project/frontend/src/pages/PatientDetailPage.test.tsx`, add a test that mounts the page for a patient with one claim (mock `GET /api/patients/:id/claims` to return one claim in the existing MSW/fetch mock setup used by the other tests in this file) and asserts a "Claims" heading and the claim's amount/type render. Match the mocking style already used in that test file for visits — reuse its handler-registration helper. Example assertion body:

```tsx
expect(await screen.findByRole('heading', { name: /claims/i })).toBeInTheDocument()
expect(await screen.findByText(/outpatient/i)).toBeInTheDocument()
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd new-project/frontend && npm test -- PatientDetailPage`
Expected: FAIL — no "Claims" heading.

- [ ] **Step 4: Add the Claims section**

In `PatientDetailPage.tsx`, import the claim hooks and `ClaimForm`, then add a Claims section directly after the Visits section, mirroring the Visits wiring:

```tsx
import { useClaims, useCreateClaim, useDeleteClaim } from '../api/claims'
import ClaimForm from '../components/ClaimForm'
import { ApiError } from '../api/client'
```

Inside the component (mirror how visits do it):

```tsx
const claims = useClaims(patientId)
const createClaim = useCreateClaim(patientId)
const deleteClaim = useDeleteClaim(patientId)
const [claimErrors, setClaimErrors] = useState<Record<string, string>>({})
```

And in the JSX, after the Visits `</section>`:

```tsx
<section>
  <h2>Claims</h2>
  <ul>
    {claims.data?.map((c) => (
      <li key={c.id}>
        {c.claim_date} — {c.claim_type} — ${c.claim_amount} — {c.claim_status}
        <button onClick={() => deleteClaim.mutate(c.id)}>Delete</button>
      </li>
    ))}
  </ul>
  <ClaimForm
    pending={createClaim.isPending}
    fieldErrors={claimErrors}
    onSubmit={(body) => {
      setClaimErrors({})
      createClaim.mutate(body, {
        onError: (err) => {
          if (err instanceof ApiError) setClaimErrors(err.fieldErrors())
        },
      })
    }}
  />
</section>
```

Adjust `patientId`, `useState` import, and any naming to match what the file already uses (from Step 1).

- [ ] **Step 5: Run to verify it passes**

Run: `cd new-project/frontend && npm test -- PatientDetailPage`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add new-project/frontend/src/pages/PatientDetailPage.tsx new-project/frontend/src/pages/PatientDetailPage.test.tsx
git commit -m "feat(frontend): add claims section to patient detail page"
```

---

### Task 7: Add employment/income inputs to the patient form

**Files:**
- Modify: `new-project/frontend/src/api/types.ts` (extend `Patient`/`PatientCreate`)
- Modify: `new-project/frontend/src/components/PatientForm.tsx`
- Modify: `new-project/frontend/src/components/PatientForm` test if one exists, else `PatientForm` is covered via page tests.

**Interfaces:**
- Consumes: existing `PatientForm` structure.
- Produces: `employment_status` + `income` on the `Patient`/`PatientCreate` types and as inputs in the form.

- [ ] **Step 1: Extend the Patient TS types**

In `new-project/frontend/src/api/types.ts`, add to `interface Patient` and `interface PatientCreate`:

```typescript
  employment_status?: 'employed' | 'unemployed' | 'retired' | 'student' | null
  income?: number | null
```

(Add to `Patient` as non-optional-nullable `| null` fields matching the existing style, and to `PatientCreate` as optional.)

- [ ] **Step 2: Read PatientForm and add the two inputs**

Run: read `new-project/frontend/src/components/PatientForm.tsx`. Add controlled inputs mirroring its existing optional fields: an `employment_status` `<select>` (options: employed/unemployed/retired/student, plus a blank default) and an `income` numeric input (`type="number" min="0"`). Include both in the object passed to `onSubmit`, sending `employment_status: value || null` and `income: income === '' ? null : Number(income)`.

- [ ] **Step 3: Type-check and run frontend tests**

Run: `cd new-project/frontend && npm run build && npm test`
Expected: build passes; all tests pass.

- [ ] **Step 4: Commit**

```bash
git add new-project/frontend/src/api/types.ts new-project/frontend/src/components/PatientForm.tsx
git commit -m "feat(frontend): collect patient employment status and income"
```

---

### Task 8: Production schema migration for existing Postgres

**Files:**
- Create: `new-project/migrations/2026-07-01-add-claims.sql`

**Context:** `create_db_and_tables()` calls `SQLModel.metadata.create_all`, which creates the **new** `claim` table automatically on the live DB, but does **NOT** add the two new columns to the existing `patient` table. Those need an explicit `ALTER`. Tests are unaffected (they build the schema fresh each run).

**Interfaces:**
- Produces: an idempotent SQL script for the operator to run once against the Railway/Neon Postgres.

- [ ] **Step 1: Write the migration script**

Create `new-project/migrations/2026-07-01-add-claims.sql`:

```sql
-- Run once against the production Postgres after deploying the Claim model.
-- The `claim` table itself is created automatically by SQLModel.create_all on
-- startup; only the new patient columns need a manual ALTER.
ALTER TABLE patient ADD COLUMN IF NOT EXISTS employment_status VARCHAR;
ALTER TABLE patient ADD COLUMN IF NOT EXISTS income DOUBLE PRECISION;
```

- [ ] **Step 2: Document how to run it**

Add a short note to `new-project/migrations/2026-07-01-add-claims.sql` header (already above) and verify the file exists.

Run: `ls new-project/migrations/2026-07-01-add-claims.sql`
Expected: the path prints.

- [ ] **Step 3: Commit**

```bash
git add new-project/migrations/2026-07-01-add-claims.sql
git commit -m "chore: add prod migration for patient employment/income columns"
```

- [ ] **Step 4: (Operator, manual — not automated) apply to prod**

When deploying, run the SQL against the live DB (e.g. `psql "$DATABASE_URL" -f new-project/migrations/2026-07-01-add-claims.sql`). This is a deploy step, not a code step — note it in the PR description.

---

## Final verification

- [ ] Run full backend suite: `cd new-project && uv run pytest -q` — all pass.
- [ ] Run frontend build + tests: `cd new-project/frontend && npm run build && npm test` — all pass.
- [ ] Manually confirm route order: claims routes resolve before the SPA fallback (they're registered in `main.py` before the catch-all).
