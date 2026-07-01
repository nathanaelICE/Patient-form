# Insurance Claim Data Model — Design

**Date:** 2026-07-01
**Status:** Approved (pending spec review)

## Purpose

Align the patient-registration app's data model with the shape of insurance
claim data (modeled on the Kaggle *Enhanced Health Insurance Claims Dataset*),
so that later work — an "acceptance subspace" that projects a submitted claim
onto the space of accepted claims and explains deviations — has a schema and
CRUD surface to build on.

This task lands **only** the schema + CRUD. All ML / subspace / projection
logic is explicitly out of scope (see Deferred).

## Background: dataset shape vs. app shape

The Kaggle dataset is a **flat, denormalized** table — one row per claim, with
patient, provider, and claim fields repeated on every row. The app is
**normalized**: `Patient` (identity/demographics) and `Visit` (an encounter)
are separate tables. The 18 dataset columns therefore split into three homes:

| Dataset column | Home |
|---|---|
| PatientAge | derived from `Patient.date_of_birth` (not stored) |
| PatientGender | `Patient.gender` (exists) |
| PatientMaritalStatus | `Patient.marital_status` (exists) |
| PatientIncome | `Patient.income` (new) |
| PatientEmploymentStatus | `Patient.employment_status` (new) |
| ProviderID, ProviderSpecialty, ProviderLocation | embedded on `Claim` |
| ClaimID | becomes our own `Claim.id` (their surrogate key not imported) |
| ClaimAmount, ClaimDate, DiagnosisCode, ProcedureCode, ClaimStatus, ClaimType, ClaimSubmissionMethod | `Claim` (new table) |

## Decisions

1. **Claim is its own entity**, separate from `Visit` (a claim ≠ a clinical
   encounter; its `diagnosis_code` is the insurance-coded diagnosis, distinct
   from `Visit.diagnosis`).
2. **Provider fields embedded on `Claim`** (no separate `Provider` table yet) —
   keeps the grain identical to the flat dataset; promote to a real table later
   if it earns its place.
3. **Claim belongs to a `Patient` (required) with an optional `visit_id`** —
   every claim has a patient; optionally bridge to the clinical encounter.
4. **New patient demographics** `employment_status` and `income` live on
   `Patient` (they describe the person, not a claim).
5. **UI: per-patient "Claims" section** on the patient detail page now; a global
   claims page is deferred until the subspace feature needs it.

## 1. Data model (`models.py`)

Extend `Patient` with two nullable fields:

```python
employment_status: Optional[str] = None   # employed/unemployed/retired/student
income: Optional[float] = None            # annual, USD
```

New `Claim` table:

```python
class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    visit_id: Optional[int] = Field(default=None, foreign_key="visit.id")
    claim_date: date
    claim_amount: float
    diagnosis_code: Optional[str] = None
    procedure_code: Optional[str] = None
    claim_status: str = "pending"             # approved/denied/pending
    claim_type: str                           # inpatient/outpatient/emergency/routine
    claim_submission_method: str              # online/paper/phone
    provider_id: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

No soft-delete on claims (matches `Visit`).

## 2. Schemas + validation (`schemas.py`)

New validation sets, following the existing `VALID_MARITAL` / `VALID_BLOOD`
pattern:

```python
VALID_EMPLOYMENT = {"employed", "unemployed", "retired", "student"}
VALID_CLAIM_STATUS = {"approved", "denied", "pending"}
VALID_CLAIM_TYPE = {"inpatient", "outpatient", "emergency", "routine"}
VALID_CLAIM_METHOD = {"online", "paper", "phone"}
```

- `ClaimCreate` / `ClaimRead` / `ClaimUpdate`, mirroring the `Visit*` trio.
- `claim_amount` and `income`: must be `>= 0`.
- Enum fields: lowercased and checked against the sets (reuse the
  `marital_status` validator pattern).
- Codes and provider fields: `_normalize_optional_str` (blank → `None`).
- `PatientCreate` / `PatientRead` / `PatientUpdate` gain `employment_status`
  (validated against `VALID_EMPLOYMENT`) and `income` (`>= 0`).

## 3. Router (`routers/claims.py`)

New `APIRouter`, gated by `get_admin`, registered in `main.py` **before** the
SPA catch-all route. Endpoints mirror the visits router:

- `POST /api/patients/{patient_id}/claims` — create
- `GET  /api/patients/{patient_id}/claims` — list for a patient
- `PATCH /api/claims/{claim_id}` — update
- `DELETE /api/claims/{claim_id}` — hard delete (matches visits)

Each endpoint verifies the patient exists and is not soft-deleted
(`deleted_at == None`), the same guard the visits router uses.

## 4. Frontend

- `src/api/` — add claim fetch functions + TypeScript types alongside the visit
  ones (single `apiFetch` wrapper, `credentials: 'include'`).
- Patient detail page — a **"Claims" section** beside "Visits," reusing the
  visit list/form pattern (React Query, `ApiError.fieldErrors()` for form
  errors).
- Patient registration/edit form — add `employment_status` (select) and
  `income` (number) inputs.
- No new route or nav entry; global Claims page deferred.

## 5. Testing

- Backend `tests/test_claims.py` (using `admin_client`): create / list / update
  / delete, patient-scoping, enum rejection, negative-amount rejection,
  soft-deleted-patient guard. Extend patient tests for the two new fields.
- Frontend vitest: claims section (render list, submit form, surface field
  errors), following the existing visit tests.

## Deferred (out of scope)

- ICD-10 / procedure-code validation
- The acceptance-subspace / projection logic and any ML
- A global claims page and navigation entry
- A normalized `Provider` table
- Any Kaggle data import / ingestion
