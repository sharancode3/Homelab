from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from typing import List, Generator

from app.api.dependencies import get_current_user, get_authz_repo
from app.api.baas_storage_models import FileMetadataResponse, StorageQuotaResponse
from app.api.baas_storage_service import BaaSStorageService, StorageLimitExceededException, StorageFileNotFoundException
from app.auth import decode_token

router = APIRouter(prefix="/api/v1/baas/projects/{project_id}/storage", tags=["baas_storage"])

def get_storage_service() -> BaaSStorageService:
    raise NotImplementedError()

def verify_storage_access(
    project_id: str,
    authorization: str | None = Header(None, description="Bearer token"),
    x_project_api_key: str | None = Header(None, alias="X-Project-API-Key"),
    authz_repo = Depends(get_authz_repo)
) -> str:
    # Attempt 1: API Key
    if x_project_api_key:
        parts = x_project_api_key.split('_')
        if len(parts) == 4 and parts[0] == 'pk' and parts[1] == 'live':
            key_id = parts[2]
            secret = parts[3]
            key_record = authz_repo.get_api_key(key_id)
            if key_record and key_record["is_active"] and key_record["project_id"] == project_id:
                import hashlib, secrets
                expected_hash = key_record["secret_hash"]
                actual_hash = hashlib.sha256(secret.encode('utf-8')).hexdigest()
                if secrets.compare_digest(expected_hash, actual_hash):
                    return f"apikey_{key_id}"
                else:
                    raise HTTPException(status_code=401, detail=f"Hash mismatch {expected_hash} vs {actual_hash}")
            else:
                raise HTTPException(status_code=401, detail=f"Key record not found or inactive for {key_id} and {project_id}")
        raise HTTPException(status_code=401, detail=f"Invalid API key format {parts}")

    # Attempt 2: Bearer Token (Developer or End-User)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
        try:
            # Check if it's an end-user token
            payload = decode_token(token, expected_aud="end_user")
            if payload.get("project_id") != project_id:
                raise HTTPException(status_code=403, detail="Token not valid for this project")
            return payload.get("sub")
        except Exception:
            pass # Not a valid end-user token, let's try developer token

        try:
            payload = decode_token(token, expected_aud="developer")
            user_id = payload.get("sub")
            role = authz_repo.get_role(project_id, user_id)
            if role in ["owner", "admin", "developer"]:
                return user_id
            raise HTTPException(status_code=403, detail="Insufficient developer permissions for this project")
        except HTTPException as e:
            raise e
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    raise HTTPException(status_code=401, detail="Authentication required")

@router.post("/", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    uploader_id: str = Depends(verify_storage_access),
    storage_service: BaaSStorageService = Depends(get_storage_service)
):
    # content_length is required to enforce quota proactively
    content_length = file.size if file.size is not None else 0
    if content_length == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size unknown or empty")

    mime_type = file.content_type or "application/octet-stream"
    
    try:
        metadata = storage_service.upload_file(
            project_id=project_id,
            filename=file.filename,
            mime_type=mime_type,
            uploader_id=uploader_id,
            content_length=content_length,
            stream=file.file
        )
        return metadata
    except StorageLimitExceededException as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{file_id}")
def download_file(
    project_id: str,
    file_id: str,
    uploader_id: str = Depends(verify_storage_access),
    storage_service: BaaSStorageService = Depends(get_storage_service)
):
    try:
        metadata, stream = storage_service.download_file(project_id, file_id)
        return StreamingResponse(
            stream,
            media_type=metadata["mime_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{metadata["filename"]}"'
            }
        )
    except StorageFileNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    project_id: str,
    file_id: str,
    uploader_id: str = Depends(verify_storage_access),
    storage_service: BaaSStorageService = Depends(get_storage_service)
):
    try:
        storage_service.delete_file(project_id, file_id)
    except StorageFileNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

@router.get("/", response_model=List[FileMetadataResponse])
def list_files(
    project_id: str,
    uploader_id: str = Depends(verify_storage_access),
    storage_service: BaaSStorageService = Depends(get_storage_service)
):
    return storage_service.list_files(project_id)
