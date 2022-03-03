from typing import Optional, Union

from fastapi import Request
from fastapi_users.manager import BaseUserManager, InvalidPasswordException

from api.accounts.models import AccountCreate, AccountDB
from common.settings import settings

SECRET = settings.jwt_secret


class AccountManager(BaseUserManager[AccountCreate, AccountDB]):
    user_db_model = AccountDB
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(
        self, account: AccountDB, request: Optional[Request] = None
    ):
        print(f"Account {account.id} has registered.")

    async def on_after_forgot_password(
        self, account: AccountDB, token: str, request: Optional[Request] = None
    ):
        print(f"Account {account.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, account: AccountDB, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for account {account.id}.")
        print(f"Verification token: {token}")

    async def validate_password(
        self,
        password: str,
        user: Union[AccountCreate, AccountDB],
    ) -> None:
        if len(password) < 8:
            raise InvalidPasswordException(
                reason="Password should be at least 8 characters."
            )
        if user.email in password:
            raise InvalidPasswordException(
                reason="Password should not contain the e-mail address."
            )
