import sys
from unittest.mock import MagicMock

# Mock pydantic
pydantic_mock = MagicMock()

class BaseModelMock:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

pydantic_mock.BaseModel = BaseModelMock
pydantic_mock.Field = lambda default_factory=None, **kwargs: default_factory() if default_factory else None
sys.modules["pydantic"] = pydantic_mock

# Mock fastapi
fastapi_mock = MagicMock()
router_mock = MagicMock()
router_mock.post = lambda *args, **kwargs: lambda f: f
router_mock.get = lambda *args, **kwargs: lambda f: f
fastapi_mock.APIRouter = lambda *args, **kwargs: router_mock
fastapi_mock.Depends = lambda x: x
fastapi_mock.HTTPException = Exception
sys.modules["fastapi"] = fastapi_mock
