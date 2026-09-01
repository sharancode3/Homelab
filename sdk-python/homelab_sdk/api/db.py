from typing import Dict, Any, List

class DbClient:
    def __init__(self, client):
        self.client = client

    def insert(self, project_id: str, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/data/{table_name}",
            json=data,
            require_api_key=True
        )

    def list(self, project_id: str, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/data/{table_name}",
            params={"limit": limit, "offset": offset},
            require_api_key=True
        )

    def get(self, project_id: str, table_name: str, row_id: str) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/data/{table_name}/{row_id}",
            require_api_key=True
        )

    def update(self, project_id: str, table_name: str, row_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.request(
            "PUT",
            f"/api/v1/baas/projects/{project_id}/data/{table_name}/{row_id}",
            json=data,
            require_api_key=True
        )

    def delete(self, project_id: str, table_name: str, row_id: str) -> None:
        self.client.request(
            "DELETE",
            f"/api/v1/baas/projects/{project_id}/data/{table_name}/{row_id}",
            require_api_key=True
        )
