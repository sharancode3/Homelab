from homelab_sdk import HomelabClient
import uuid

class TaskManager:
    """
    A standalone application class that manages tasks via the Homelab SDK.
    It does not know anything about the backend databases or Caddy.
    It only knows about HomelabClient and its public interfaces.
    """
    def __init__(self, endpoint: str, project_id: str, api_key: str):
        self.project_id = project_id
        # We explicitly disable SSL verification here for local development against the Homelab test instance.
        self.client = HomelabClient(
            base_url=endpoint,
            project_id=project_id,
            api_key=api_key,
            verify_ssl=False
        )
        self.table_name = "tasks"

    def create_task(self, title: str, description: str) -> str:
        """Create a new task in the tasks table."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "pending"
        }
        res = self.client.db.insert(self.project_id, self.table_name, payload)
        return task_id

    def list_tasks(self):
        """Retrieve all tasks."""
        return self.client.db.list(self.project_id, self.table_name)

    def complete_task(self, task_id: str):
        """Update a task's status to completed."""
        # First retrieve to ensure it exists (and to show we can use get)
        task = self.client.db.get(self.project_id, self.table_name, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        payload = task["data"]
        payload["status"] = "completed"
        return self.client.db.update(self.project_id, self.table_name, task_id, payload)

    def attach_file(self, task_id: str, filename: str, content: bytes):
        """Upload a file to Homelab storage and link it conceptually to a task."""
        storage_filename = f"{task_id}_{filename}"
        res = self.client.storage.upload(self.project_id, storage_filename, content)
        return res["id"]

    def download_attachment(self, file_id: str) -> bytes:
        """Download an attachment from Homelab storage."""
        return self.client.storage.download(self.project_id, file_id)

    def remove_task(self, task_id: str):
        """Delete a task."""
        self.client.db.delete(self.project_id, self.table_name, task_id)

if __name__ == "__main__":
    print("TaskManager standalone CLI loaded.")
