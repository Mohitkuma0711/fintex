from fastapi import APIRouter

from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.extractions import router as extractions_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.me import router as me_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.tax import router as tax_router
from app.core.config import get_settings

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(me_router, tags=["profile"])
router.include_router(documents_router, tags=["documents"])
router.include_router(extractions_router, tags=["verification"])
router.include_router(tax_router)
router.include_router(chat_router)
router.include_router(reports_router)

if get_settings().storage_backend == "local":
    from app.api.v1.routes.dev_storage import router as dev_storage_router

    router.include_router(dev_storage_router, tags=["dev"])
