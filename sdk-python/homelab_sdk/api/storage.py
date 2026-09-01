from typing import Dict, Any, List

class StorageClient:
    def __init__(self, client):
        self.client = client

    def upload(self, project_id: str, filename: str, content: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Upload a file to project storage."""
        # Note: Storage can accept Dev Token, API Key, or End User Token.
        # We will use whichever is available in the client, but prefer API key for data plane.
        # This will use the base headers logic of HomelabClient implicitly if we don't pass strict requirements.
        # However, to maintain boundary, if api_key is present, we enforce it.
        require_api_key = bool(self.client.api_key)
        require_end_user_token = bool(self.client.end_user_token) and not require_api_key
        require_dev_token = bool(self.client.developer_token) and not (require_api_key or require_end_user_token)

        files = {"file": (filename, content, content_type)}
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/storage/",
            files=files,
            require_api_key=require_api_key,
            require_end_user_token=require_end_user_token,
            require_dev_token=require_dev_token
        )

    def list(self, project_id: str) -> List[Dict[str, Any]]:
        """List files in project storage."""
        require_api_key = bool(self.client.api_key)
        require_end_user_token = bool(self.client.end_user_token) and not require_api_key
        require_dev_token = bool(self.client.developer_token) and not (require_api_key or require_end_user_token)

        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/storage/",
            require_api_key=require_api_key,
            require_end_user_token=require_end_user_token,
            require_dev_token=require_dev_token
        )

    def download(self, project_id: str, file_id: str) -> bytes:
        """Download a file from project storage."""
        require_api_key = bool(self.client.api_key)
        require_end_user_token = bool(self.client.end_user_token) and not require_api_key
        require_dev_token = bool(self.client.developer_token) and not (require_api_key or require_end_user_token)

        url = f"{self.client.base_url}/api/v1/baas/projects/{project_id}/storage/{file_id}"
        headers = self.client._build_headers(
            require_dev_token=require_dev_token,
            require_api_key=require_api_key,
            require_end_user_token=require_end_user_token
        )

        # We handle this manually because we want bytes back, not JSON
        response = self.client.session.get(url, headers=headers)
        if 200 <= response.status_code < 300:
            return response.content
        self.client._handle_response(response) # This will raise the appropriate error

    def delete(self, project_id: str, file_id: str) -> None:
        """Delete a file from project storage."""
        require_api_key = bool(self.client.api_key)
        require_end_user_token = bool(self.client.end_user_token) and not require_api_key
        require_dev_token = bool(self.client.developer_token) and not (require_api_key or require_end_user_token)

        self.client.request(
            "DELETE",
            f"/api/v1/baas/projects/{project_id}/storage/{file_id}",
            require_api_key=require_api_key,
            require_end_user_token=require_end_user_token,
            require_dev_token=require_dev_token
        )
