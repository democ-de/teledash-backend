from enum import Enum
from typing import Optional

from api.utils import remove_none_values_from_dict
from api.validators import OrderEnum, SortParams, parse_sort_params
from common.database.models.chat import ChatType


def parse_chat_filter(
    type: Optional[ChatType] = None,
    is_verified: Optional[bool] = None,
    is_restricted: Optional[bool] = None,
    is_scam: Optional[bool] = None,
    is_fake: Optional[bool] = None,
) -> dict:
    result = {
        "type": type,
        "is_verified": is_verified,
        "is_restricted": is_restricted,
        "is_scam": is_scam,
        "is_fake": is_fake,
    }

    return remove_none_values_from_dict(result)


class ChatSortBy(str, Enum):
    username = "username"
    title = "title"  # type: ignore
    members_count = "members_count"
    updated_at = "updated_at"
    scraped_at = "scraped_at"


def parse_chat_sort(
    sort_by: Optional[ChatSortBy] = None,
    order: Optional[OrderEnum] = None,
) -> SortParams:
    return parse_sort_params(sort_by, order)
