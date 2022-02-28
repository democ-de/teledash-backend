from typing import Any, List, Tuple

from fastapi import Query
from pydantic import BaseModel

from common.database.models.chat import ChatOut
from common.database.models.client import ClientOut
from common.database.models.message import MessageOut
from common.database.models.user import UserOut

PaginationParams = Tuple[int, int, int]


class Pagination:
    def __init__(self, maximum_limit: int = 100):
        self.maximum_limit = maximum_limit

    def parse_params(
        self,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=0),
    ) -> PaginationParams:
        capped_limit = min(self.maximum_limit, limit)
        return (skip, capped_limit, self.maximum_limit)

    # Alternative pagination
    # async def page_size(
    #     self,
    #     page: int = Query(1, ge=1),
    #     size: int = Query(10, ge=0),
    # ) -> Tuple[int, int]:
    #     capped_size = min(self.maximum_limit, size)
    #     return (page, capped_size)


class PaginatedResponseInfo(BaseModel):
    offset: int
    limit: int
    max_limit: int


class PaginatedResponse(BaseModel):
    data: List[Any]
    pagination: PaginatedResponseInfo

    @classmethod
    def create(cls, data: List[Any], params: PaginationParams) -> "PaginatedResponse":
        offset, limit, max_limit = params
        return cls(
            data=data,
            pagination=PaginatedResponseInfo(
                offset=offset, limit=limit, max_limit=max_limit
            ),
        )


class PaginatedChats(PaginatedResponse):
    data: List[ChatOut]


class PaginatedMessages(PaginatedResponse):
    data: List[MessageOut]


class PaginatedUsers(PaginatedResponse):
    data: List[UserOut]


class PaginatedClients(PaginatedResponse):
    data: List[ClientOut]
