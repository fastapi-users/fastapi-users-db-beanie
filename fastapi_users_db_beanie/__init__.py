"""FastAPI Users database adapter for Beanie."""
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from beanie import Document, PydanticObjectId
from fastapi_users.db.base import BaseUserDatabase
from pydantic import BaseModel
from pymongo import IndexModel
from pymongo.collation import Collation


__version__ = "0.0.0"


class BeanieBaseUser(Document):
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    class Collection:
        email_collation = Collation("en", strength=2)
        indexes = [
            IndexModel("email", unique=True),
            IndexModel(
                "email", name="case_insensitive_email_index", collation=email_collation
            ),
        ]


UP_BEANIE = TypeVar("UP_BEANIE", bound=BeanieBaseUser)


class BaseOAuthAccount(BaseModel):
    oauth_name: str
    access_token: str
    account_id: str
    account_email: str
    expires_at: Optional[int] = None
    refresh_token: Optional[str] = None


class BeanieUserDatabase(
    Generic[UP_BEANIE], BaseUserDatabase[UP_BEANIE, PydanticObjectId]
):
    """
    Database adapter for Beanie.

    :param user_model: Beanie user model.
    :param oauth_account_model: Optional Beanie OAuth account model.
    """

    def __init__(
        self,
        user_model: Type[UP_BEANIE],
        oauth_account_model: Optional[Type[BaseOAuthAccount]] = None,
    ):
        self.user_model = user_model
        self.oauth_account_model = oauth_account_model

    async def get(self, id: PydanticObjectId) -> Optional[UP_BEANIE]:
        """Get a single user by id."""
        return await self.user_model.get(id)

    async def get_by_email(self, email: str) -> Optional[UP_BEANIE]:
        """Get a single user by email."""
        return await self.user_model.find_one(
            self.user_model.email == email,
            collation=self.user_model.Collection.email_collation,
        )

    async def get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> Optional[UP_BEANIE]:
        """Get a single user by OAuth account id."""
        if self.oauth_account_model is None:
            raise NotImplementedError()

        return await self.user_model.find_one(
            {
                "oauth_accounts.oauth_name": oauth,
                "oauth_accounts.account_id": account_id,
            }
        )

    async def create(self, create_dict: Dict[str, Any]) -> UP_BEANIE:
        """Create a user."""
        user = self.user_model(**create_dict)
        return await user.insert()

    async def update(self, user: UP_BEANIE, update_dict: Dict[str, Any]) -> UP_BEANIE:
        """Update a user."""
        for key, value in update_dict.items():
            setattr(user, key, value)
        return await user.save()

    async def delete(self, user: UP_BEANIE) -> None:
        """Delete a user."""
        await user.delete()

    async def add_oauth_account(
        self, user: UP_BEANIE, create_dict: Dict[str, Any]
    ) -> UP_BEANIE:
        """Create an OAuth account and add it to the user."""
        if self.oauth_account_model is None:
            raise NotImplementedError()

        oauth_account = self.oauth_account_model(**create_dict)
        user.oauth_accounts.append(oauth_account)  # type: ignore

        return await user.save()

    async def update_oauth_account(
        self,
        user: UP_BEANIE,
        oauth_account: BaseOAuthAccount,
        update_dict: Dict[str, Any],
    ) -> UP_BEANIE:
        """Update an OAuth account on a user."""
        if self.oauth_account_model is None:
            raise NotImplementedError()

        for i, existing_oauth_account in enumerate(user.oauth_accounts):  # type: ignore
            if (
                existing_oauth_account.oauth_name == oauth_account.oauth_name
                and existing_oauth_account.account_id == oauth_account.account_id
            ):
                for key, value in update_dict.items():
                    setattr(user.oauth_accounts[i], key, value)  # type: ignore

        return await user.save()
