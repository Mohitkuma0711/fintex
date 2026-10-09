import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.v1.dependencies import get_storage
from app.core.config import Settings, get_settings
from app.services.storage.local_storage import LocalStorage

router = APIRouter()


@router.get("/dev-storage/{object_path:path}")
async def serve_local_document(
    object_path: str,
    settings: Settings = Depends(get_settings),
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    if settings.storage_backend != "local" or not isinstance(storage, LocalStorage):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found.")
    try:
        path = storage.resolve(object_path)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type or "application/octet-stream")
