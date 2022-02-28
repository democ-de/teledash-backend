from datetime import datetime, timedelta
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.chats.validators import parse_chat_filter, parse_chat_sort
from api.database import get_database
from api.database.aggregations import aggregate_metrics
from api.database.client import Database
from api.pagination import PaginatedChats, Pagination
from api.validators import parse_projection_params, parse_search_params
from common.database.models.chat import ChatIn, ChatMetrics, ChatOut


def get_chats_router(app):

    router = APIRouter()
    current_active_verified_user = get_current_active_verified_user()
    pagination = Pagination(maximum_limit=100)

    @router.get(
        "/chats",
        response_description="List all chats",
        tags=["chats"],
        response_model=PaginatedChats,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def list_chats(
        filter: dict = Depends(parse_chat_filter),
        sort: dict = Depends(parse_chat_sort),
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
            async for doc in database.chats.find(
                filter,
                projection=projection,
                skip=offset,
                limit=limit,
                sort=sort,
            )
        ]

        return PaginatedChats.create(data=result, params=pagination)

    @app.get(
        "/chats/{id}",
        response_description="Get a single chat",
        tags=["chats"],
        response_model=ChatOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def get_chat(
        id: int,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        chat = await database.chats.find_one({"_id": id})

        if not chat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        activity_total = await aggregate_metrics(
            database,
            {"metadata.chat_id": id, "metadata.type": "message_posted"},
            "$sum",
        )

        growth_total = await aggregate_metrics(
            database,
            {"metadata.chat_id": id, "metadata.type": "chat_members_count"},
            "$avg",
        )

        yesterday = datetime.utcnow() - timedelta(days=1)
        activity_last_day = await aggregate_metrics(
            database,
            {
                "metadata.chat_id": id,
                "metadata.type": "message_posted",
                "ts": {"$gte": yesterday},
            },
            "$sum",
        )

        growth_last_day = await aggregate_metrics(
            database,
            {
                "metadata.chat_id": id,
                "metadata.type": "chat_members_count",
                "ts": {"$gte": yesterday},
            },
            "$avg",
        )

        chat.metrics = ChatMetrics(
            activity_total=activity_total,
            growth_total=growth_total,
            activity_last_day=activity_last_day,
            growth_last_day=growth_last_day,
        )

        # TODO: paginate members

        return chat

    @router.put(
        "/chats/{id}",
        response_description="Update a chat",
        tags=["chats"],
        response_model=ChatOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def update_chat(
        id: int,
        chat: ChatIn,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        response = await database.chats.update_one(
            {"_id": id},
            {"$set": chat.dict(exclude_unset=True, exclude_none=True, by_alias=True)},
        )

        if response.modified_count == 1:
            return await database.chats.find_one({"_id": id})

        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=f"Chat with id {id} was not updated",
        )

    return router
