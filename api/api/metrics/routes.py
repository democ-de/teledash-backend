from fastapi import APIRouter, Depends

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.database import get_database
from api.database.aggregations import aggregate_metrics
from api.database.client import Database
from common.database.models.chat import GlobalMetrics


def get_metrics_router(app):

    router = APIRouter()

    @router.get(
        "/metrics",
        response_description="List all metrics",
        tags=["metrics"],
        response_model=GlobalMetrics,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def list_metrics(
        account: Account = Depends(get_current_active_verified_user()),
        database: Database = Depends(get_database),
    ):

        users_count = await database.users.count({})
        chats_count = await database.chats.count({})
        messages_count = await database.messages.count({})
        photos_count = await database.messages.count({"attachment.type": "photo"})
        videos_count = await database.messages.count({"attachment.type": "video"})
        voices_count = await database.messages.count({"attachment.type": "voice"})

        activity_total = await aggregate_metrics(
            database,
            {"metadata.type": "message_posted"},
            "$sum",
        )

        growth_total = await aggregate_metrics(
            database,
            {"metadata.type": "chat_members_count"},
            "$avg",
        )

        metrics = GlobalMetrics(
            users_count=users_count,
            chats_count=chats_count,
            messages_count=messages_count,
            photos_count=photos_count,
            activity_total=activity_total,
            growth_total=growth_total,
            videos_count=videos_count,
            voices_count=voices_count,
        )

        return metrics

    return router
