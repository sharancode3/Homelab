import shutil
import tempfile
import unittest
from pathlib import Path

from app.providers.storage.exceptions import ArtifactNotFoundError, ArtifactWriteError
from app.providers.storage.local_storage import LocalStorageProvider


class LocalStorageProviderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.provider = LocalStorageProvider(self.temp_dir)
        self.test_content = b"test artifact content"
        self.test_path = "backups/proj_1/artifact.tar.gz"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_create_and_read_artifact(self) -> None:
        # Create
        ref = self.provider.create_artifact(self.test_path, self.test_content)
        self.assertEqual(ref, self.test_path)
        
        # Verify it exists on disk
        artifact_path = Path(self.temp_dir) / "backups/proj_1/artifact.tar.gz"
        self.assertTrue(artifact_path.exists())
        self.assertTrue(Path(str(artifact_path) + ".sha256").exists())
        
        # Read
        content = self.provider.read_artifact(ref)
        self.assertEqual(content, self.test_content)

    def test_verify_artifact(self) -> None:
        ref = self.provider.create_artifact(self.test_path, self.test_content)
        
        # Verify correct checksum
        self.assertTrue(self.provider.verify_artifact(ref))
        
        # Tamper with content
        artifact_path = Path(self.temp_dir) / self.test_path
        artifact_path.write_bytes(b"tampered content")
        
        # Verify should now fail
        self.assertFalse(self.provider.verify_artifact(ref))

    def test_missing_artifact(self) -> None:
        with self.assertRaises(ArtifactNotFoundError):
            self.provider.read_artifact("nonexistent/artifact.txt")
            
        self.assertFalse(self.provider.verify_artifact("nonexistent/artifact.txt"))

    def test_delete_artifact(self) -> None:
        ref = self.provider.create_artifact(self.test_path, self.test_content)
        self.provider.delete_artifact(ref)
        
        with self.assertRaises(ArtifactNotFoundError):
            self.provider.read_artifact(ref)
            
        # Verify parent directory cleanup
        parent_dir = Path(self.temp_dir) / "backups/proj_1"
        self.assertFalse(parent_dir.exists())

    def test_directory_traversal_prevention(self) -> None:
        with self.assertRaises(ArtifactWriteError):
            self.provider.create_artifact("../outside.txt", b"data")


if __name__ == "__main__":
    unittest.main()
