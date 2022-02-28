from datetime import timedelta
from typing import Dict, List, Literal

from common.database.models.aggregations import AggregatedMetrics


def generate_metrics_aggregation_pipeline(
    match: Dict,
    accumulator: Literal["$sum", "$avg"],
    time_delta: timedelta = timedelta(hours=1),
) -> List:
    match = {
        "$match": match,
    }

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

    # TODO: Add minutes option to grou_by_date
    # if time_delta == timedelta(minutes=1):
    #     group_by_date["minute"] = "$date.minute"

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

    # TODO: Add minutes option to format_date

    transform = {
        "$project": {
            "_id": 0,  # remove field "_id" from response
            "date": {"$toDate": {"$concat": format_date}},  # rebuild datetime
            "value": {"$round": ["$value", 0]},  # round values
        }
    }

    sort = {"$sort": {"date": 1}}  # sort by date ascending

    return [match, project, group, transform, sort]


def transform_growth_activity_metrics(
    aggregations,
    accumulator: Literal["$sum", "$avg"],
    time_delta: timedelta = timedelta(hours=1),
) -> AggregatedMetrics:
    metrics_aggregated = AggregatedMetrics()

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
                new_value = 0 if accumulator == "$sum" else None

            data.append(new_value)
            current_date += time_delta

        # fill up data to return at least 24 values (1 day)
        while len(data) <= 23:
            new_value = 0 if accumulator == "$sum" else None
            data.append(new_value)

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
        metrics_aggregated.time_delta = int(time_delta.total_seconds())
        metrics_aggregated.data = data

    return metrics_aggregated
