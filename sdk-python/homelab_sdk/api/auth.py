from typing import Dict, Any

class AuthClient:
    def __init__(self, client):
        self.client = client

    def register(self, project_id: str, email: str, password: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        payload = {"email": email, "password": password}
        if metadata:
            payload["metadata"] = metadata
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/register",
            json=payload
        )

    def login(self, project_id: str, email: str, password: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/login",
            json={"email": email, "password": password}
        )

    def verify_email(self, project_id: str, email: str, token: str) -> None:
        self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/verify-email",
            json={"email": email, "token": token}
        )

    def reset_password_request(self, project_id: str, email: str) -> None:
        self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/reset-password-request",
            json={"email": email}
        )

    def reset_password(self, project_id: str, token: str, new_password: str) -> None:
        self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/reset-password",
            json={"token": token, "new_password": new_password}
        )

    def get_me(self, project_id: str) -> Dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/baas/projects/{project_id}/auth/me",
            require_end_user_token=True
        )

    def refresh(self, project_id: str, refresh_token: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/refresh",
            json={"refresh_token": refresh_token}
        )

    def logout(self, project_id: str) -> None:
        self.client.request(
            "POST",
            f"/api/v1/baas/projects/{project_id}/auth/logout",
            require_end_user_token=True
        )
