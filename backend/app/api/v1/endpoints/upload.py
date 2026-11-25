from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from starlette.concurrency import run_in_threadpool
from app.services.document_text import extract_document_text
from app.shared.responses import APIResponse
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()

# 10 MB payload cap — previously the entire upload was read into RAM with no
# limit, which allowed trivial denial-of-service via huge files.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@router.post("/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 10 MB.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    filename = file.filename or "uploaded-file"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in {"pdf", "docx", "txt", "eml"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please upload PDF, DOCX, TXT, or EML."
        )
    try:
        text = await run_in_threadpool(extract_document_text, extension, content)
    except Exception:
        # Do not forward raw parser exception text to the client.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not extract text from the uploaded file '{filename}'. "
                   "The file may be corrupted or not a valid document.",
        )

    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text was found in the uploaded file.",
        )
    
    return APIResponse(
        success=True, 
        message="Text extracted", 
        data={"text": text, "filename": filename}
    )
