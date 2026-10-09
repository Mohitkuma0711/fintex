from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile, status

from app.api.v1.dependencies import get_document_service, get_extraction_job
from app.core.auth import get_current_user
from app.models import Document, User
from app.schemas.api import DocumentResponse
from app.schemas.extraction import DocumentExtractionResponse, DocumentUploadResponse
from app.services.documents import DocumentService
from app.services.extraction.jobs import ExtractionJob

router = APIRouter()


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="List the authenticated user's document metadata",
)
async def list_documents(
    user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[Document]:
    return await service.list(user)


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a private PDF, JPG, or PNG and start extraction",
    description=(
        "Validates file signature, extension, MIME type, and size. Stores the file "
        "in a private per-user Supabase Storage path and queues extraction."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ...,
        description="PDF, JPG, or PNG; maximum size is configured by the server.",
    ),
    document_type: Literal["form16", "salary_slip"] = Form("form16"),
    auto_delete_after_30_days: bool = Form(False),
    user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    extraction_job: ExtractionJob = Depends(get_extraction_job),
) -> DocumentUploadResponse:
    content = await file.read(service.settings.max_upload_size_bytes + 1)
    response, document = await service.upload(
        user=user,
        file_name=file.filename or "",
        declared_content_type=file.content_type or "",
        content=content,
        document_type=document_type,
        auto_delete_after_30_days=auto_delete_after_30_days,
    )
    background_tasks.add_task(extraction_job.run, document.id)
    return response


@router.get(
    "/documents/{document_id}/extraction",
    response_model=DocumentExtractionResponse,
    summary="Get document scan and extraction status",
)
async def get_document_extraction(
    document_id: UUID,
    user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentExtractionResponse:
    return await service.get_extraction(user, document_id)


@router.post(
    "/documents/{document_id}/retry",
    response_model=DocumentExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed document extraction",
)
async def retry_document_extraction(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    extraction_job: ExtractionJob = Depends(get_extraction_job),
) -> DocumentExtractionResponse:
    await service.retry_extraction(user, document_id)
    background_tasks.add_task(extraction_job.run, document_id)
    return await service.get_extraction(user, document_id)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document from private storage",
)
async def delete_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    await service.delete(user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
