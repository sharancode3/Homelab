from typing import Dict, Any

class AdminClient:
    def __init__(self, client):
        self.client = client

    def register(self, email: str, username: str, password: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            "/api/v1/auth/register",
            json={"email": email, "username": username, "password": password}
        )

    def login(self, email: str, password: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )

    def get_me(self) -> Dict[str, Any]:
        return self.client.request("GET", "/api/v1/auth/me", require_dev_token=True)

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        return self.client.request(
            "POST",
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

    def logout(self) -> None:
        self.client.request("POST", "/api/v1/auth/logout", require_dev_token=True)
