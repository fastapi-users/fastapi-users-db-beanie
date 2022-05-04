from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pymongo.errors
import pytest
from beanie import PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from fastapi_users_db_beanie.access_token import (
    BeanieAccessTokenDatabase,
    BeanieBaseAccessToken,
)


class AccessToken(BeanieBaseAccessToken[PydanticObjectId]):
    pass


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
async def beanie_access_token_db(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[BeanieAccessTokenDatabase, None]:
    database: AsyncIOMotorDatabase = mongodb_client["test_database"]
    await init_beanie(database=database, document_models=[AccessToken])

    yield BeanieAccessTokenDatabase(AccessToken)

    await mongodb_client.drop_database("test_database")


@pytest.fixture
def user_id() -> PydanticObjectId:
    return PydanticObjectId()


@pytest.mark.asyncio
async def test_queries(
    beanie_access_token_db: BeanieAccessTokenDatabase[AccessToken],
    user_id: PydanticObjectId,
):
    access_token_create = {"token": "TOKEN", "user_id": user_id}

    # Create
    access_token = await beanie_access_token_db.create(access_token_create)
    assert access_token.token == "TOKEN"
    assert access_token.user_id == user_id

    # Update
    update_dict = {"created_at": datetime.now(timezone.utc)}
    updated_access_token = await beanie_access_token_db.update(
        access_token, update_dict
    )
    assert updated_access_token.created_at == update_dict["created_at"]

    # Get by token
    access_token_by_token = await beanie_access_token_db.get_by_token(
        access_token.token
    )
    assert access_token_by_token is not None

    # Get by token expired
    access_token_by_token = await beanie_access_token_db.get_by_token(
        access_token.token, max_age=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    assert access_token_by_token is None

    # Get by token not expired
    access_token_by_token = await beanie_access_token_db.get_by_token(
        access_token.token, max_age=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    assert access_token_by_token is not None

    # Get by token unknown
    access_token_by_token = await beanie_access_token_db.get_by_token(
        "NOT_EXISTING_TOKEN"
    )
    assert access_token_by_token is None

    # Delete token
    await beanie_access_token_db.delete(access_token)
    deleted_access_token = await beanie_access_token_db.get_by_token(access_token.token)
    assert deleted_access_token is None


@pytest.mark.asyncio
async def test_insert_existing_token(
    beanie_access_token_db: BeanieAccessTokenDatabase[AccessToken],
    user_id: PydanticObjectId,
):
    access_token_create = {"token": "TOKEN", "user_id": user_id}
    await beanie_access_token_db.create(access_token_create)

    with pytest.raises(pymongo.errors.DuplicateKeyError):
        await beanie_access_token_db.create(access_token_create)
