import json
from enum import Enum
from typing import List, Optional, Tuple

from fastapi import Query


class OrderEnum(str, Enum):
    ascending = "asc"
    descending = "desc"


def parse_search_params(
    search: Optional[str] = Query(None, min_length=2, max_length=80)
) -> dict:
    # See MongoDB text search syntax:
    # https://docs.mongodb.com/manual/text-search/
    # TODO: Specify language for improved results:
    # https://docs.mongodb.com/manual/reference/text-search-languages/
    return {"$text": {"$search": search}} if search else {}


SortParams = List[Tuple[str, int]]


def parse_sort_params(
    sort_by: Optional[str] = None,
    order_dir: Optional[OrderEnum] = None,
) -> SortParams:
    if not sort_by:
        return []

    order = -1 if order_dir == OrderEnum.descending else 1
    sort = [(sort_by, order)]

    return sort


def parse_projection_params(
    projection: Optional[str] = Query(None),
):
    # see https://docs.mongodb.com/manual/tutorial/project-fields-from-query-results
    if not projection:
        return None

    # TODO: maybe validate projection dict
    return json.loads(projection)
