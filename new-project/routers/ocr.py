from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select

from deps import get_admin
from database import get_session
from models import AdminUser, OcrJob
from schemas import OcrJobRead
import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/status")
def ocr_status(_: AdminUser = Depends(get_admin)):
    return {"available": ocr_service.ocr_available()}


@router.post("/extract")
async def extract(file: UploadFile = File(...), _: AdminUser = Depends(get_admin)):
    if not ocr_service.ocr_available():
        raise HTTPException(status_code=503, detail="OCR is not configured")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        return ocr_service.extract_patient_fields(data, file.content_type)
    except ocr_service.OCRError:
        raise HTTPException(status_code=502, detail="OCR extraction failed")


@router.post("/jobs", response_model=List[OcrJobRead], status_code=201)
async def create_jobs(
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    if not ocr_service.ocr_available():
        raise HTTPException(status_code=503, detail="OCR is not configured")
    # Read + validate all first so a single bad file creates no jobs.
    staged = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {f.filename}")
        data = await f.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"Empty file: {f.filename}")
        staged.append((f.filename or "upload", f.content_type, data))

    jobs = [OcrJob(filename=name, media_type=mt, image=img) for name, mt, img in staged]
    for job in jobs:
        session.add(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return jobs


@router.get("/jobs", response_model=List[OcrJobRead])
def list_jobs(session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    return session.exec(select(OcrJob).order_by(OcrJob.created_at, OcrJob.id)).all()


@router.post("/jobs/{job_id}/retry", response_model=OcrJobRead)
def retry_job(job_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    job = session.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "error":
        raise HTTPException(status_code=409, detail="Only errored jobs can be retried")
    job.status = "pending"
    job.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def dismiss_job(job_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    job = session.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(job)
    session.commit()
