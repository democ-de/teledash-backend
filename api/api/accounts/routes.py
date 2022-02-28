from fastapi import APIRouter, Depends, Response

from api.accounts.auth import (
    auth_backend,
    get_current_active_verified_user,
    get_fast_api_users,
    get_jwt_strategy,
)
from api.accounts.models import Account


def get_accounts_router(app):

    router = APIRouter()
    fastapi_users = get_fast_api_users()
    current_active_verified_user = get_current_active_verified_user()

    router.include_router(
        fastapi_users.get_auth_router(
            auth_backend,
            # if is_verified=false response will be 400 Bad Request
            requires_verification=True,
        ),
        prefix="/auth/jwt",
        tags=["auth"],
    )

    @router.post(
        "/auth/jwt/refresh",
        tags=["auth"],
    )
    async def refresh_jwt(
        response: Response,
        account: Account = Depends(current_active_verified_user),
    ):
        return {
            'access_token': await get_jwt_strategy().write_token(account)
        }

    router.include_router(
        fastapi_users.get_register_router(), prefix="/auth", tags=["auth"]
    )

    router.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth",
        tags=["auth"],
    )

    router.include_router(
        fastapi_users.get_verify_router(),
        prefix="/auth",
        tags=["auth"],
    )

    router.include_router(
        fastapi_users.get_users_router(), prefix="/accounts", tags=["accounts"]
    )

    return router
