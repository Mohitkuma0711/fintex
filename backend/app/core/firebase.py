import firebase_admin
import structlog
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from firebase_admin import firestore as firebase_firestore

from app.core.config import Settings

logger = structlog.get_logger(__name__)


def initialize_firebase(settings: Settings) -> None:
    if not firebase_admin._apps:
        credential = (
            credentials.Certificate(settings.firebase_service_account_path)
            if settings.firebase_service_account_path
            else credentials.ApplicationDefault()
        )
        options = {}
        if settings.firebase_project_id:
            options["projectId"] = settings.firebase_project_id
        if settings.firebase_storage_bucket:
            options["storageBucket"] = settings.firebase_storage_bucket
        firebase_admin.initialize_app(credential, options)


def get_firestore_client():
    if not firebase_admin._apps:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return firebase_firestore.client()


def verify_id_token(token: str) -> dict:
    if not firebase_admin._apps:
        raise RuntimeError("Firebase not initialized.")
    return firebase_auth.verify_id_token(token)


def is_firebase_initialized() -> bool:
    return bool(firebase_admin._apps)


def sync_user_document(
    *,
    user_id: str,
    firebase_uid: str | None = None,
    email: str | None = None,
    display_name: str | None = None,
    preferred_financial_year: str | None = None,
    confirmed_profile: dict[str, object] | None = None,
) -> None:
    if not is_firebase_initialized():
        return
    payload: dict[str, object] = {
        "userId": user_id,
        "email": email,
        "displayName": display_name,
        "preferredFinancialYear": preferred_financial_year,
        "confirmedProfile": confirmed_profile,
    }
    if firebase_uid is not None:
        payload["firebaseUid"] = firebase_uid
    try:
        get_firestore_client().collection("users").document(user_id).set(payload, merge=True)
    except Exception as error:
        logger.warning("firestore_user_sync_failed", error_type=type(error).__name__)
