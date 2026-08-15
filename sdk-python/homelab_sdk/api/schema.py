from typing import Dict, Any, List

class SchemaClient:
    def __init__(self, client):
        self.client = client

    def create(self, project_id: str, name: str, columns: Dict[str, str]) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/tables",
            json={"name": name, "columns": columns},
            require_dev_token=True
        )

    def list(self, project_id: str) -> List[Dict[str, Any]]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/tables",
            require_dev_token=True
        )

    def get(self, project_id: str, table_name: str) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/tables/{table_name}",
            require_dev_token=True
        )

    def delete(self, project_id: str, table_name: str) -> None:
        self.client.request(
            "DELETE",
            f"/api/v1/baas/projects/{project_id}/tables/{table_name}",
            require_dev_token=True
        )
