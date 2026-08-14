from pydantic import BaseModel, ConfigDict
from datetime import datetime

class FileMetadataResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    uploaded_by: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class StorageQuotaResponse(BaseModel):
    usage_bytes: int
    quota_bytes: int
    max_file_size_bytes: int
    is_exceeded: bool
