from typing import Dict, Any, List

class ApiKeysClient:
    def __init__(self, client):
        self.client = client

    def create(self, project_id: str, name: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/keys",
            json={"name": name},
            require_dev_token=True
        )

    def list(self, project_id: str) -> List[Dict[str, Any]]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/keys",
            require_dev_token=True
        )

    def revoke(self, project_id: str, key_id: str) -> None:
        self.client.request(
            "DELETE",
            f"/api/v1/baas/projects/{project_id}/keys/{key_id}",
            require_dev_token=True
        )

    def rotate(self, project_id: str, key_id: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/keys/{key_id}/rotate",
            require_dev_token=True
        )
