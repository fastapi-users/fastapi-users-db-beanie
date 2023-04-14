from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
)

from beanie import Document, PydanticObjectId
from fastapi_users.authentication.strategy.db import AccessTokenDatabase
from pydantic import BaseModel, Field
from pymongo import IndexModel


class BeanieBaseAccessToken(BaseModel):
    token: str
    user_id: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        indexes = [IndexModel("token", unique=True)]


class BeanieBaseAccessTokenDocument(BeanieBaseAccessToken, Document):  # type: ignore
    pass


AP_BEANIE = TypeVar("AP_BEANIE", bound=BeanieBaseAccessTokenDocument)


class BeanieAccessTokenDatabase(Generic[AP_BEANIE], AccessTokenDatabase[AP_BEANIE]):
    """
    Access token database adapter for Beanie.

    :param access_token_model: Beanie access token model.
    """

    def __init__(self, access_token_model: Type[AP_BEANIE]):
        self.access_token_model = access_token_model

    async def get_by_token(
        self, token: str, max_age: Optional[datetime] = None
    ) -> Optional[AP_BEANIE]:
        query: Dict[str, Any] = {"token": token}
        if max_age is not None:
            query["created_at"] = {"$gte": max_age}
        return await self.access_token_model.find_one(query)

    async def create(self, create_dict: Dict[str, Any]) -> AP_BEANIE:
        access_token = self.access_token_model(**create_dict)
        await access_token.create()
        return access_token

    async def update(
        self, access_token: AP_BEANIE, update_dict: Dict[str, Any]
    ) -> AP_BEANIE:
        for key, value in update_dict.items():
            setattr(access_token, key, value)
        await access_token.save()
        return access_token

    async def delete(self, access_token: AP_BEANIE) -> None:
        await access_token.delete()
