import requests
from typing import Optional, Dict, Any, TypeVar, Type, cast
from requests.exceptions import RequestException
from .exceptions import (
    HomelabAPIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    RateLimitError,
    ServerError
)

from .api.admin import AdminClient
from .api.projects import ProjectsClient
from .api.teammates import TeammatesClient
from .api.apikeys import ApiKeysClient
from .api.schema import SchemaClient
from .api.db import DbClient
from .api.storage import StorageClient
from .api.auth import AuthClient

class HomelabClient:
    def __init__(
        self,
        base_url: str = "https://localhost:8443",
        developer_token: Optional[str] = None,
        project_id: Optional[str] = None,
        api_key: Optional[str] = None,
        end_user_token: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize the HomelabClient with specific credentials based on the intended plane.

        Management Plane (Admin/Projects): Provide `developer_token`.
        Data Plane (Database/Storage): Provide `project_id` and `api_key` (or `end_user_token`).
        End-User Plane (Identity): Provide `project_id` and optionally `end_user_token`.
        """
        self.base_url = base_url.rstrip("/")
        self.developer_token = developer_token
        self.project_id = project_id
        self.api_key = api_key
        self.end_user_token = end_user_token
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.verify = self.verify_ssl

        # Instantiate management plane endpoints
        self.admin = AdminClient(self)
        self.projects = ProjectsClient(self)
        self.teammates = TeammatesClient(self)
        self.apikeys = ApiKeysClient(self)
        self.schema = SchemaClient(self)

        # Instantiate data plane endpoints
        self.db = DbClient(self)
        self.storage = StorageClient(self)
        self.auth = AuthClient(self)

    def _build_headers(self, require_dev_token: bool = False, require_api_key: bool = False, require_end_user_token: bool = False, is_multipart: bool = False) -> Dict[str, str]:
        headers = {}
        if not is_multipart:
            headers["Content-Type"] = "application/json"

        # Enforce strict separate credential usage
        provided_creds = sum([bool(self.developer_token), bool(self.api_key), bool(self.end_user_token)])

        if require_dev_token:
            if not self.developer_token:
                raise ValueError("A developer_token is required for this operation.")
            headers["Authorization"] = f"Bearer {self.developer_token}"

        elif require_api_key:
            if not self.api_key:
                raise ValueError("An api_key is required for this operation.")
            headers["X-Project-API-Key"] = self.api_key

        elif require_end_user_token:
            if not self.end_user_token:
                raise ValueError("An end_user_token is required for this operation.")
            headers["Authorization"] = f"Bearer {self.end_user_token}"

        return headers

    def _handle_response(self, response: requests.Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}

        if 200 <= response.status_code < 300:
            return data

        # Map to appropriate HTTP exceptions
        detail = data.get("detail", str(data))
        if response.status_code == 401:
            raise AuthenticationError(detail, response.status_code, data)
        elif response.status_code == 403:
            raise AuthorizationError(detail, response.status_code, data)
        elif response.status_code == 404:
            raise NotFoundError(detail, response.status_code, data)
        elif response.status_code in (400, 422):
            raise ValidationError(detail, response.status_code, data)
        elif response.status_code == 409:
            raise ConflictError(detail, response.status_code, data)
        elif response.status_code == 429:
            raise RateLimitError(detail, response.status_code, data)
        elif response.status_code >= 500:
            raise ServerError(detail, response.status_code, data)

        raise HomelabAPIError(detail, response.status_code, data)

    def request(self, method: str, path: str, require_dev_token: bool = False, require_api_key: bool = False, require_end_user_token: bool = False, **kwargs) -> Any:
        url = f"{self.base_url}{path}"

        headers = kwargs.pop("headers", {})
        is_multipart = "files" in kwargs
        headers.update(self._build_headers(require_dev_token, require_api_key, require_end_user_token, is_multipart=is_multipart))

        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            # 204 No Content has no JSON body
            if response.status_code == 204:
                return None
            return self._handle_response(response)
        except RequestException as e:
            raise HomelabAPIError(f"Network request failed: {str(e)}")
