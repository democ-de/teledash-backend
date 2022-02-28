from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi.param_functions import Query

from api.validators import OrderEnum, SortParams, parse_sort_params
from common.database.models.message.attachment import MessageAttachmentType


def parse_message_filter(
    from_user_ids: Optional[List[int]] = Query(None, alias="from_user_ids[]"),
    chat_ids: Optional[List[int]] = Query(None, alias="chat_ids[]"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_empty: Optional[bool] = None,
    attachment_type: Optional[MessageAttachmentType] = None,
) -> dict:
    result = {}

    if from_user_ids:
        result["from_user._id"] = {"$in": from_user_ids}
    if chat_ids:
        result["chat._id"] = {"$in": chat_ids}
    if date_from:
        result["date"] = {"$gte": date_from}
        if date_to:
            result["date"]["$lt"] = date_to
    if is_empty:
        result["is_empty"] = is_empty
    if attachment_type:
        result["attachment.type"] = attachment_type

    return result


class MessageSortBy(str, Enum):
    message_id = "message_id"
    date = "date"
    views = "views"


def parse_message_sort(
    sort_by: Optional[MessageSortBy] = None,
    order: Optional[OrderEnum] = None,
) -> SortParams:
    return parse_sort_params(sort_by, order)
