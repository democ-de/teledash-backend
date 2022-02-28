from datetime import timedelta
from typing import Dict, Literal

from api.database.client import Database
from common.database.models.chat.metrics import ChatMetricsAggregated


# TODO: Optimize and combine with worker/aggregations.py
async def aggregate_chat_metrics(
    database: Database,
    match: Dict,
    accumulator: Literal["$sum", "$avg"],
    time_delta: timedelta = timedelta(hours=1),
) -> ChatMetricsAggregated:

    match = {"$match": match}

    project = {
        "$project": {
            "date": {"$dateToParts": {"date": "$ts"}},
            "value": 1,
        }
    }

    group_by_date = {
        "year": "$date.year",
        "month": "$date.month",
        "day": "$date.day",
        "hour": "$date.hour",
    }

    group = {
        "$group": {
            "_id": {
                "date": group_by_date,
            },
            "value": {accumulator: "$value"},
        }
    }

    # if time_delta == timedelta(minutes=1):
    #     group_by_date["minutes"] = "$date.minute"

    format_date = [
        {"$toString": "$_id.date.year"},
        "-",
        {"$toString": "$_id.date.month"},
        "-",
        {"$toString": "$_id.date.day"},
        " ",
        {"$toString": "$_id.date.hour"},
        ":00",
    ]

    transform = {
        "$project": {
            "_id": 0,  # remove field "_id" from response
            "date": {"$toDate": {"$concat": format_date}},  # rebuild datetime
            "value": {"$round": ["$value", 0]},  # round values
        }
    }

    sort = {"$sort": {"date": 1}}  # sort by date ascending

    pipeline = [match, project, group, transform, sort]

    aggregations = [doc async for doc in database.metrics.aggregate(pipeline)]

    metrics_aggregated = ChatMetricsAggregated()

    if aggregations:
        start_date = aggregations[0]["date"]
        end_date = aggregations[-1]["date"]

        data = []
        current_date = start_date
        i = 0
        while current_date <= end_date:
            if current_date == aggregations[i]["date"]:
                new_value = aggregations[i]["value"]
                i += 1
            else:
                new_value = None

            data.append(new_value)
            current_date += time_delta

        if accumulator == "$sum":
            # sum of all values (e.g. message_posted)
            metrics_aggregated.sum = sum(filter(None, data))

        if accumulator == "$avg":
            # diff of last and first value (e.g. member_count)
            metrics_aggregated.diff = (
                aggregations[-1]["value"] - aggregations[0]["value"]
            )

        metrics_aggregated.start_date = start_date
        metrics_aggregated.end_date = end_date
        # metrics_aggregated.time_delta = time_delta  # TODO: Fix mymongo encoding
        metrics_aggregated.data = data

    return metrics_aggregated
