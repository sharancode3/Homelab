import uuid
from typing import BinaryIO, Dict, Any, List, Tuple
from app.config.settings import config
from app.adapters.interfaces import StorageAdapter
from app.storage.providers.sqlite_tenant import BaaSStorageRepository, TenantDatabaseError

class StorageLimitExceededException(Exception):
    pass

class StorageFileNotFoundException(Exception):
    pass

class BaaSStorageService:
    def __init__(self, storage_repo: BaaSStorageRepository, storage_adapter: StorageAdapter):
        self._storage_repo = storage_repo
        self._storage_adapter = storage_adapter
        self.max_file_size = config.storage_max_file_size_bytes
        self.max_project_quota = config.storage_max_project_quota_bytes

    def _get_artifact_path(self, project_id: str, file_id: str) -> str:
        # Secure server-side path resolution
        return f"projects/{project_id}/storage/{file_id}"

    def upload_file(
        self,
        project_id: str,
        filename: str,
        mime_type: str,
        uploader_id: str,
        content_length: int,
        stream: BinaryIO
    ) -> Dict[str, Any]:
        
        # Check overall project quota before starting stream
        current_usage = self._storage_repo.get_project_storage_usage(project_id)
        if current_usage + content_length > self.max_project_quota:
            raise StorageLimitExceededException(f"Upload exceeds project storage quota of {self.max_project_quota} bytes")

        if content_length > self.max_file_size:
            raise StorageLimitExceededException(f"File size exceeds maximum allowed size of {self.max_file_size} bytes")

        file_id = f"file_{uuid.uuid4().hex}"
        artifact_path = self._get_artifact_path(project_id, file_id)

        # Custom stream reader to enforce max_file_size strictly during read
        class LimitStream:
            def __init__(self, raw_stream, limit):
                self.raw_stream = raw_stream
                self.limit = limit
                self.bytes_read = 0

            def read(self, size=-1):
                chunk = self.raw_stream.read(size)
                if chunk:
                    self.bytes_read += len(chunk)
                    if self.bytes_read > self.limit:
                        raise StorageLimitExceededException(f"Streamed file exceeded maximum allowed size of {self.limit} bytes")
                return chunk

        limited_stream = LimitStream(stream, self.max_file_size)

        try:
            self._storage_adapter.create_artifact_stream(artifact_path, limited_stream)
            # Read checksum that the local adapter generated
            checksum_path = self._storage_adapter._get_checksum_path(self._storage_adapter._get_artifact_path(artifact_path))
            checksum = checksum_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            raise RuntimeError(f"Storage adapter failed: {str(e)}")

        # Re-check overall quota post-upload in case of concurrent uploads
        final_size = limited_stream.bytes_read
        if current_usage + final_size > self.max_project_quota:
            self._storage_adapter.delete_artifact(artifact_path)
            raise StorageLimitExceededException("Project quota exceeded during concurrent uploads")

        import datetime
        metadata = {
            "id": file_id,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": final_size,
            "checksum": checksum,
            "uploaded_by": uploader_id,
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        try:
            self._storage_repo.insert_file_metadata(project_id, metadata)
            # Fetch it back to get the DB-generated created_at timestamp
            return self._storage_repo.get_file_metadata(project_id, file_id)
        except TenantDatabaseError as e:
            self._storage_adapter.delete_artifact(artifact_path)
            raise RuntimeError(f"Failed to save file metadata: {str(e)}")

    def download_file(self, project_id: str, file_id: str) -> Tuple[Dict[str, Any], Any]:
        metadata = self._storage_repo.get_file_metadata(project_id, file_id)
        if not metadata:
            raise StorageFileNotFoundException("File metadata not found")

        artifact_path = self._get_artifact_path(project_id, file_id)
        try:
            stream = self._storage_adapter.read_artifact_stream(artifact_path)
            return metadata, stream
        except Exception:
            raise StorageFileNotFoundException("Physical file not found")

    def delete_file(self, project_id: str, file_id: str) -> None:
        metadata = self._storage_repo.get_file_metadata(project_id, file_id)
        if not metadata:
            raise StorageFileNotFoundException("File metadata not found")

        artifact_path = self._get_artifact_path(project_id, file_id)
        self._storage_adapter.delete_artifact(artifact_path)
        self._storage_repo.delete_file_metadata(project_id, file_id)

    def list_files(self, project_id: str) -> List[Dict[str, Any]]:
        return self._storage_repo.list_files_metadata(project_id)

    def get_quota(self, project_id: str) -> Dict[str, Any]:
        usage = self._storage_repo.get_project_storage_usage(project_id)
        return {
            "usage_bytes": usage,
            "quota_bytes": self.max_project_quota,
            "max_file_size_bytes": self.max_file_size,
            "is_exceeded": usage >= self.max_project_quota
        }
