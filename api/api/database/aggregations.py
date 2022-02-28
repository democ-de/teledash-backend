from datetime import timedelta
from typing import Dict, Literal

from api.database.client import Database
from common.database.aggregations import (
    generate_metrics_aggregation_pipeline,
    transform_growth_activity_metrics,
)
from common.database.models.aggregations import AggregatedMetrics


async def aggregate_metrics(
    database: Database,
    match: Dict,
    accumulator: Literal["$sum", "$avg"],
    time_delta: timedelta = timedelta(hours=1),
) -> AggregatedMetrics:

    pipeline = generate_metrics_aggregation_pipeline(match, accumulator, time_delta)

    aggregations = [doc async for doc in database.metrics.aggregate(pipeline)]

    metrics_aggregated = transform_growth_activity_metrics(
        aggregations, accumulator, time_delta
    )

    return metrics_aggregated
