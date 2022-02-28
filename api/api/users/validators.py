from enum import Enum
from typing import Optional

from api.utils import remove_none_values_from_dict
from api.validators import OrderEnum, SortParams, parse_sort_params


def parse_user_filter(
    is_deleted: Optional[bool] = None,
    is_bot: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    is_restricted: Optional[bool] = None,
    is_scam: Optional[bool] = None,
    is_fake: Optional[bool] = None,
    is_support: Optional[bool] = None,
    phone_number: Optional[str] = None,
) -> dict:
    result = {
        "is_deleted": is_deleted,
        "is_bot": is_bot,
        "is_verified": is_verified,
        "is_restricted": is_restricted,
        "is_scam": is_scam,
        "is_fake": is_fake,
        "is_support": is_support,
        "phone_number": phone_number,
    }

    return remove_none_values_from_dict(result)


class UserSortBy(str, Enum):
    updated_at = "updated_at"


def parse_user_sort(
    sort_by: Optional[UserSortBy] = None,
    order: Optional[OrderEnum] = None,
) -> SortParams:
    return parse_sort_params(sort_by, order)
