from typing import Any, AsyncGenerator, Dict, List, Optional

import pymongo.errors
import pytest
from beanie import PydanticObjectId, init_beanie
from fastapi_users import InvalidID
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import Field

from fastapi_users_db_beanie import (
    BaseOAuthAccount,
    BeanieBaseUser,
    BeanieUserDatabase,
    ObjectIDIDMixin,
)


class User(BeanieBaseUser[PydanticObjectId]):
    first_name: Optional[str] = None


class OAuthAccount(BaseOAuthAccount):
    pass


class UserOAuth(User):
    oauth_accounts: List[OAuthAccount] = Field(default_factory=list)


@pytest.fixture(scope="module")
async def mongodb_client():
    client = AsyncIOMotorClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=10000,
        uuidRepresentation="standard",
    )

    try:
        await client.server_info()
        yield client
        client.close()
    except pymongo.errors.ServerSelectionTimeoutError:
        pytest.skip("MongoDB not available", allow_module_level=True)
        return


@pytest.fixture
async def beanie_user_db(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[BeanieUserDatabase, None]:
    database: AsyncIOMotorDatabase = mongodb_client["test_database"]
    await init_beanie(database=database, document_models=[User])

    yield BeanieUserDatabase(User)

    await mongodb_client.drop_database("test_database")


@pytest.fixture
async def beanie_user_db_oauth(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[BeanieUserDatabase, None]:
    database: AsyncIOMotorDatabase = mongodb_client["test_database"]
    await init_beanie(database=database, document_models=[UserOAuth])

    yield BeanieUserDatabase(UserOAuth, OAuthAccount)

    await mongodb_client.drop_database("test_database")


@pytest.mark.asyncio
async def test_queries(
    beanie_user_db: BeanieUserDatabase[User, PydanticObjectId],
    oauth_account1: Dict[str, Any],
):
    user_create = {
        "email": "lancelot@camelot.bt",
        "hashed_password": "guinevere",
    }

    # Create
    user = await beanie_user_db.create(user_create)
    assert user.id is not None
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.email == user_create["email"]

    # Update
    updated_user = await beanie_user_db.update(user, {"is_superuser": True})
    assert updated_user.is_superuser is True

    # Get by id
    id_user = await beanie_user_db.get(user.id)
    assert id_user is not None
    assert id_user.id == user.id
    assert id_user.is_superuser is True

    # Get by email
    email_user = await beanie_user_db.get_by_email(str(user_create["email"]))
    assert email_user is not None
    assert email_user.id == user.id

    # Get by uppercased email
    email_user = await beanie_user_db.get_by_email("Lancelot@camelot.bt")
    assert email_user is not None
    assert email_user.id == user.id

    # Unknown user
    unknown_user = await beanie_user_db.get_by_email("galahad@camelot.bt")
    assert unknown_user is None

    # Delete user
    await beanie_user_db.delete(user)
    deleted_user = await beanie_user_db.get(user.id)
    assert deleted_user is None

    # OAuth without defined table
    with pytest.raises(NotImplementedError):
        await beanie_user_db.get_by_oauth_account("foo", "bar")
    with pytest.raises(NotImplementedError):
        await beanie_user_db.add_oauth_account(user, {})
    with pytest.raises(NotImplementedError):
        oauth_account = OAuthAccount(**oauth_account1)
        await beanie_user_db.update_oauth_account(user, oauth_account, {})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "email,query,found",
    [
        ("lancelot@camelot.bt", "lancelot@camelot.bt", True),
        ("lancelot@camelot.bt", "LanceloT@camelot.bt", True),
        ("lancelot@camelot.bt", "lancelot.@camelot.bt", False),
        ("lancelot@camelot.bt", "lancelot.*", False),
        ("lancelot@camelot.bt", "lancelot+guinevere@camelot.bt", False),
        ("lancelot+guinevere@camelot.bt", "lancelot+guinevere@camelot.bt", True),
        ("lancelot+guinevere@camelot.bt", "lancelot.*", False),
        ("квіточка@пошта.укр", "квіточка@пошта.укр", True),
        ("квіточка@пошта.укр", "КВІТОЧКА@ПОШТА.УКР", True),
    ],
)
async def test_email_query(
    beanie_user_db: BeanieUserDatabase[User, PydanticObjectId],
    email: str,
    query: str,
    found: bool,
):
    user_create = {
        "email": email,
        "hashed_password": "guinevere",
    }
    user = await beanie_user_db.create(user_create)

    email_user = await beanie_user_db.get_by_email(query)

    if found:
        assert email_user is not None
        assert email_user.id == user.id
    else:
        assert email_user is None


@pytest.mark.asyncio
async def test_insert_existing_email(
    beanie_user_db: BeanieUserDatabase[User, PydanticObjectId]
):
    user_create = {
        "email": "lancelot@camelot.bt",
        "hashed_password": "guinevere",
    }
    await beanie_user_db.create(user_create)

    with pytest.raises(pymongo.errors.DuplicateKeyError):
        await beanie_user_db.create(user_create)


@pytest.mark.asyncio
async def test_queries_custom_fields(
    beanie_user_db: BeanieUserDatabase[User, PydanticObjectId],
):
    """It should output custom fields in query result."""
    user_create = {
        "email": "lancelot@camelot.bt",
        "hashed_password": "guinevere",
        "first_name": "Lancelot",
    }
    user = await beanie_user_db.create(user_create)

    assert user.id is not None
    id_user = await beanie_user_db.get(user.id)
    assert id_user is not None
    assert id_user.id == user.id
    assert id_user.first_name == user.first_name


@pytest.mark.asyncio
async def test_queries_oauth(
    beanie_user_db_oauth: BeanieUserDatabase[UserOAuth, PydanticObjectId],
    oauth_account1: Dict[str, Any],
    oauth_account2: Dict[str, Any],
):
    user_create = {
        "email": "lancelot@camelot.bt",
        "hashed_password": "guinevere",
    }

    # Create
    user = await beanie_user_db_oauth.create(user_create)
    assert user.id is not None

    # Add OAuth account
    user = await beanie_user_db_oauth.add_oauth_account(user, oauth_account1)
    user = await beanie_user_db_oauth.add_oauth_account(user, oauth_account2)
    assert len(user.oauth_accounts) == 2
    assert user.oauth_accounts[1].account_id == oauth_account2["account_id"]
    assert user.oauth_accounts[0].account_id == oauth_account1["account_id"]

    # Update
    user = await beanie_user_db_oauth.update_oauth_account(
        user, user.oauth_accounts[0], {"access_token": "NEW_TOKEN"}
    )
    assert user.oauth_accounts[0].access_token == "NEW_TOKEN"

    # Get by id
    assert user.id is not None
    id_user = await beanie_user_db_oauth.get(user.id)
    assert id_user is not None
    assert id_user.id == user.id
    assert id_user.oauth_accounts[0].access_token == "NEW_TOKEN"

    # Get by email
    email_user = await beanie_user_db_oauth.get_by_email(user_create["email"])
    assert email_user is not None
    assert email_user.id == user.id
    assert len(email_user.oauth_accounts) == 2

    # Get by OAuth account
    oauth_user = await beanie_user_db_oauth.get_by_oauth_account(
        oauth_account1["oauth_name"], oauth_account1["account_id"]
    )
    assert oauth_user is not None
    assert oauth_user.id == user.id

    # Unknown OAuth account
    unknown_oauth_user = await beanie_user_db_oauth.get_by_oauth_account("foo", "bar")
    assert unknown_oauth_user is None


def test_objectid_id_mixin():
    object_id_mixin = ObjectIDIDMixin()
    object_id = PydanticObjectId("62736e11bae73a7a990f7df1")

    assert object_id_mixin.parse_id("62736e11bae73a7a990f7df1") == object_id
    assert object_id_mixin.parse_id(object_id) == object_id

    with pytest.raises(InvalidID):
        object_id_mixin.parse_id("abc")

    with pytest.raises(InvalidID):
        object_id_mixin.parse_id(12346)
