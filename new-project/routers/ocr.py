from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from deps import get_admin
from models import AdminUser
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
