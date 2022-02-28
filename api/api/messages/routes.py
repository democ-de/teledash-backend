from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.database import get_database
from api.database.client import Database
from api.messages.validators import parse_message_filter, parse_message_sort
from api.pagination import PaginatedMessages, Pagination
from api.validators import parse_projection_params, parse_search_params
from common.database.models.message import MessageIn, MessageOut


def get_messages_router(app):

    router = APIRouter()
    current_active_verified_user = get_current_active_verified_user()
    pagination = Pagination(maximum_limit=50)

    @router.get(
        "/messages",
        response_description="List all messages",
        tags=["messages"],
        response_model=PaginatedMessages,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def list_messages(
        filter: dict = Depends(parse_message_filter),
        sort: dict = Depends(parse_message_sort),
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
            async for doc in database.messages.find(
                filter,
                projection=projection,
                skip=offset,
                limit=limit,
                sort=sort,
            )
        ]

        return PaginatedMessages.create(data=result, params=pagination)

    @router.get(
        "/messages/{id}",
        response_description="Get a single message",
        tags=["messages"],
        response_model=MessageOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def show_message(
        id: str,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        message = await database.messages.find_one({"_id": id})

        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return message

    @router.put(
        "/messages/{id}",
        response_description="Update a message",
        tags=["messages"],
        response_model=MessageOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def update_message(
        id: str,
        message: MessageIn,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        response = await database.messages.update_one(
            {"_id": id},
            {
                "$set": message.dict(
                    exclude_unset=True, exclude_none=True, by_alias=True
                )
            },
        )

        if response.modified_count == 1:
            return await database.messages.find_one({"_id": id})

        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=f"Message {id} was not updated",
        )

    return router
