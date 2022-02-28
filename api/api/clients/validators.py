from enum import Enum
from typing import List, Optional

from fastapi import Query

from api.chats.validators import OrderEnum
from api.utils import remove_none_values_from_dict
from api.validators import SortParams, parse_sort_params


def parse_client_filter(
    is_active: Optional[bool] = None,
    phone_number: Optional[str] = None,
    user_id: Optional[int] = None,
    chat_ids: Optional[List[int]] = Query(None),
) -> dict:
    result = {
        "is_active": is_active,
        "phone_number": phone_number,
        "user_id": user_id,
    }

    if chat_ids:
        result["chats._id"] = {"$in": chat_ids}

    return remove_none_values_from_dict(result)


class ClientSortBy(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"


def parse_client_sort(
    sort_by: Optional[ClientSortBy] = None,
    order: Optional[OrderEnum] = None,
) -> SortParams:
    return parse_sort_params(sort_by, order)
