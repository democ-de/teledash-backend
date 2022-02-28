from datetime import datetime, timedelta
from typing import cast

from celery.utils.log import get_task_logger
from minio.error import InvalidResponseError

from common.settings import settings
from common.storage import Storage
from worker.database import Database
from worker.main import app

logger = get_task_logger(__name__)


@app.task(name="files.purge_message_attachments")
def purge_message_attachments() -> dict:
    if settings.keep_attachment_files_days == 0:
        raise ValueError(
            'Trying to purge attachment files as scheduled, but setting is set to "0 days" (indefinitely)'  # noqa: E501
        )

    database = Database()
    storage = Storage()
    delete_count = 0

    # get message documents with attachments in storage
    messages_cursor = database.messages.find(
        {
            "date": {
                "$lt": datetime.utcnow()
                - timedelta(days=settings.keep_attachment_files_days)
            },
            "attachment.storage_refs": {"$exists": True},
        },
        {"_id": 1, "attachment.storage_refs": 1},
    )

    for message in messages_cursor:
        attachment = cast(dict, message.attachment)

        for ref in attachment["storage_refs"]:
            try:
                # remove object in storage
                storage.client.remove_object(ref["bucket"], ref["object"])
            except InvalidResponseError:
                logger.error(
                    f'Error removing file "{ref["bucket"]}/{ref["object"]}" from storage',  # noqa: E501
                    exc_info=True,
                )
                break
        else:
            # remove storage refs in database for message attachment
            database.messages.update_one(
                {"_id": message.id}, {"$unset": {"attachment.storage_refs": 1}}
            )

            delete_count += 1

    database.close()

    return {"delete_count": delete_count}
