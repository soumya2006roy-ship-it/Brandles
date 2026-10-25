import hashlib
import hmac
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_auth_context
from app.core.config import get_settings
from app.core.db import get_db
from app.storage.factory import get_storage

router = APIRouter(tags=["private-files"])


@router.get("/private-files/{organization_id}/{object_key:path}")
def download_private_file(organization_id: str, object_key: str, expires: int = Query(ge=1), signature: str = Query(min_length=64, max_length=64), context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    from sqlalchemy import select

    from app.db.models import Membership

    membership = db.scalar(select(Membership.id).where(Membership.organization_id == organization_id, Membership.user_id == context.user.id))
    if not membership:
        raise HTTPException(status_code=404, detail="File not found.")
    if expires < int(time()) or expires > int(time()) + 900:
        raise HTTPException(status_code=403, detail="This download link is invalid or expired.")
    payload = f"{organization_id}:{object_key}:{expires}".encode()
    expected = hmac.new(get_settings().app_secret_key.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="This download link is invalid or expired.")
    storage = get_storage()
    local_path = storage.local_path(organization_id, object_key)
    if local_path is not None:
        path = Path(local_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(path, media_type="application/octet-stream", filename=path.name, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
    stream, content_type = storage.stream(organization_id, object_key)
    return StreamingResponse(stream, media_type=content_type, headers={"Cache-Control": "private, no-store", "Content-Disposition": "attachment"})
