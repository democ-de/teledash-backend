from fastapi import Depends
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.fastapi_users import FastAPIUsers
from fastapi_users_db_mongodb import MongoDBUserDatabase

from api.accounts.manager import AccountManager
from api.accounts.models import Account, AccountCreate, AccountDB, AccountUpdate
from api.database import database
from common.settings import settings

# Full FastAPI users example see:
# https://fastapi-users.github.io/fastapi-users/configuration/full-example/#mongodb


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.jwt_secret, lifetime_seconds=settings.jwt_lifetime_seconds
    )


fastapi_users = None
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


async def get_account_db():
    yield MongoDBUserDatabase(AccountDB, database.accounts.collection)


def get_account_manager(account_db: MongoDBUserDatabase = Depends(get_account_db)):
    return AccountManager(account_db)


def init_fast_api_users() -> None:
    global fastapi_users
    fastapi_users = FastAPIUsers(
        get_account_manager,
        [auth_backend],
        Account,
        AccountCreate,
        AccountUpdate,
        AccountDB,
    )


def get_fast_api_users() -> FastAPIUsers:
    if fastapi_users is None:
        raise ValueError("Database is not initialized")

    return fastapi_users


def get_current_active_verified_user():
    return get_fast_api_users().current_user(active=True, verified=True)
