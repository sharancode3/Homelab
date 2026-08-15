from typing import Dict, Any, List

class ProjectsClient:
    def __init__(self, client):
        self.client = client

    def create(self, name: str, slug: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            "/api/v1/baas/projects/",
            json={"project_name": name, "project_slug": slug},
            require_dev_token=True
        )

    def list(self) -> List[Dict[str, Any]]:
        return self.client.request("GET", "/api/v1/baas/projects/", require_dev_token=True)

    def get(self, project_id: str) -> Dict[str, Any]:
        return self.client.request("GET", f"/api/v1/baas/projects/{project_id}", require_dev_token=True)

    def deploy(self, project_id: str, image_tag: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/deploy",
            json={"image_tag": image_tag},
            require_dev_token=True
        )

    def backup(self, project_id: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/backup",
            json={},
            require_dev_token=True
        )

    def restore(self, project_id: str, backup_id: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/restore",
            json={"backup_id": backup_id},
            require_dev_token=True
        )

    def get_health(self, project_id: str) -> Dict[str, Any]:
        return self.client.request("GET", f"/api/v1/baas/projects/{project_id}/health", require_dev_token=True)

    def get_logs(self, project_id: str, limit: int = 100) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/logs",
            params={"limit": limit},
            require_dev_token=True
        )

    def history(self, project_id: str, limit: int = 100) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/history",
            params={"limit": limit},
            require_dev_token=True
        )

    def status(self, project_id: str) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/status",
            require_dev_token=True
        )
