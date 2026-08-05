import hashlib
import os
import shutil
from pathlib import Path

from app.adapters.interfaces import StorageAdapter
from app.providers.storage.exceptions import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactWriteError,
)


class LocalStorageProvider(StorageAdapter):
    """A local filesystem implementation of the StorageAdapter contract."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_artifact_path(self, reference: str) -> Path:
        """Resolve the reference to a secure, isolated path within base_dir."""
        # Clean the reference to prevent directory traversal
        clean_ref = os.path.normpath(reference).lstrip("/")
        if ".." in clean_ref.split(os.sep):
            raise ArtifactWriteError("Invalid artifact reference path")
            
        full_path = (self.base_dir / clean_ref).resolve()
        
        if not str(full_path).startswith(str(self.base_dir)):
            raise ArtifactWriteError("Artifact path escapes base directory")
            
        return full_path

    def _get_checksum_path(self, artifact_path: Path) -> Path:
        return artifact_path.with_suffix(artifact_path.suffix + ".sha256")

    def _compute_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def create_artifact(self, path: str, content: bytes) -> str:
        artifact_path = self._get_artifact_path(path)
        checksum_path = self._get_checksum_path(artifact_path)
        
        try:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            artifact_path.write_bytes(content)
            
            # Write checksum
            checksum = self._compute_checksum(content)
            checksum_path.write_text(checksum, encoding="utf-8")
            
            return path
        except OSError as e:
            raise ArtifactWriteError(f"Failed to write artifact {path}: {e}")

    def read_artifact(self, reference: str) -> bytes:
        artifact_path = self._get_artifact_path(reference)
        
        if not artifact_path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {reference}")
            
        try:
            return artifact_path.read_bytes()
        except OSError as e:
            raise ArtifactNotFoundError(f"Failed to read artifact {reference}: {e}")

    def verify_artifact(self, reference: str) -> bool:
        artifact_path = self._get_artifact_path(reference)
        checksum_path = self._get_checksum_path(artifact_path)
        
        if not artifact_path.exists():
            return False
            
        if not checksum_path.exists():
            return False
            
        try:
            content = artifact_path.read_bytes()
            expected_checksum = checksum_path.read_text(encoding="utf-8").strip()
            actual_checksum = self._compute_checksum(content)
            
            return actual_checksum == expected_checksum
        except OSError:
            return False

    def delete_artifact(self, reference: str) -> None:
        artifact_path = self._get_artifact_path(reference)
        checksum_path = self._get_checksum_path(artifact_path)
        
        try:
            if artifact_path.exists():
                artifact_path.unlink()
            if checksum_path.exists():
                checksum_path.unlink()
                
            # Optionally clean up empty parent directories up to base_dir
            current = artifact_path.parent
            while current != self.base_dir and current.exists() and not any(current.iterdir()):
                current.rmdir()
                current = current.parent
                
        except OSError as e:
            # We swallow deletion errors or we can raise depending on requirements.
            # Local storage cleanup failure isn't always critical, but we can log it.
            pass
