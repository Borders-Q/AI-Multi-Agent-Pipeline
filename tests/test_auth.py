from skyt_platform.auth import is_token_valid
from skyt_platform.config import settings


def test_local_access_token_validation():
    assert is_token_valid(settings.access_token)
    assert not is_token_valid(f"{settings.access_token}-invalid")
