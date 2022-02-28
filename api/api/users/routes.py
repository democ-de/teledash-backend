from datetime import datetime, timedelta
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.database import get_database
from api.database.aggregations import aggregate_metrics
from api.database.client import Database
from api.pagination import PaginatedUsers, Pagination
from api.users.validators import parse_user_filter, parse_user_sort
from api.validators import parse_projection_params, parse_search_params
from common.database.models.user import UserMetrics, UserOut


def get_users_router(app):

    router = APIRouter()
    current_active_verified_user = get_current_active_verified_user()
    pagination = Pagination(maximum_limit=100)

    @router.get(
        "/users",
        response_description="List all users",
        tags=["users"],
        response_model=PaginatedUsers,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def list_users(
        filter: dict = Depends(parse_user_filter),
        sort: dict = Depends(parse_user_sort),
        search: dict = Depends(parse_search_params),
        projection: dict = Depends(parse_projection_params),
        pagination: Tuple[int, int, int] = Depends(pagination.parse_params),
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        offset, limit, max_limit = pagination

        if search:
            filter.update(search)

        result = [
            doc
            async for doc in database.users.find(
                filter,
                projection=projection,
                skip=offset,
                limit=limit,
                sort=sort,
            )
        ]

        return PaginatedUsers.create(data=result, params=pagination)

    @app.get(
        "/users/{id}",
        response_description="Get a single user",
        tags=["users"],
        response_model=UserOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def get_user(
        id: int,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        user = await database.users.find_one({"_id": id})

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        activity_total = await aggregate_metrics(
            database,
            {"metadata.user_id": id, "metadata.type": "message_posted"},
            "$sum",
        )

        yesterday = datetime.utcnow() - timedelta(days=1)
        activity_last_day = await aggregate_metrics(
            database,
            {
                "metadata.user_id": id,
                "metadata.type": "message_posted",
                "ts": {"$gte": yesterday},
            },
            "$sum",
        )

        user.metrics = UserMetrics(
            activity_total=activity_total, activity_last_day=activity_last_day
        )

        # find groups user is member of
        filter = {"members.id": user.id}
        projection = {"id": 1, "title": 1, "username": 1}
        chats_user_is_member = [
            doc
            async for doc in database.chats.find(
                filter,
                projection=projection,
            )
        ]
        user.in_chats = [chat.create_ref() for chat in chats_user_is_member]

        return user

    return router
