import pytest

@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from app.api.rate_limiter import auth_limiter, data_plane_limiter, control_plane_limiter
    auth_limiter.buckets.clear()
    data_plane_limiter.buckets.clear()
    control_plane_limiter.buckets.clear()
