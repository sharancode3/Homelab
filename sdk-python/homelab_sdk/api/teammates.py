from typing import Dict, Any, List

class TeammatesClient:
    def __init__(self, client):
        self.client = client

    def list(self, project_id: str) -> List[Dict[str, Any]]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/members",
            require_dev_token=True
        )

    def add(self, project_id: str, email: str, role: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/members",
            json={"email": email, "role": role},
            require_dev_token=True
        )

    def update_role(self, project_id: str, target_user_id: str, role: str) -> Dict[str, Any]:
        return self.client.request(
            "PUT",
            f"/api/v1/baas/projects/{project_id}/members/{target_user_id}",
            json={"role": role},
            require_dev_token=True
        )

    def remove(self, project_id: str, target_user_id: str) -> None:
        self.client.request(
            "DELETE",
            f"/api/v1/baas/projects/{project_id}/members/{target_user_id}",
            require_dev_token=True
        )
