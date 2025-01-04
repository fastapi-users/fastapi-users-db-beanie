from typing import Any

import pytest


@pytest.fixture
def oauth_account1() -> dict[str, Any]:
    return {
        "oauth_name": "service1",
        "access_token": "TOKEN",
        "expires_at": 1579000751,
        "account_id": "user_oauth1",
        "account_email": "king.arthur@camelot.bt",
    }


@pytest.fixture
def oauth_account2() -> dict[str, Any]:
    return {
        "oauth_name": "service2",
        "access_token": "TOKEN",
        "expires_at": 1579000751,
        "account_id": "user_oauth2",
        "account_email": "king.arthur@camelot.bt",
    }
