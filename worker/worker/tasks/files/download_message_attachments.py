import asyncio

# import time
from pathlib import Path
from typing import List, Union, cast

import celery
from celery.utils.log import get_task_logger
from pyrogram import types as pyrogram_types
from pyrogram.client import Client as TelegramClient

from common.database.models.message import Message
from common.database.models.pyobjectid import PyObjectId
from common.settings import settings
from common.storage import StorageBucketNames
from common.utils import run_pyrogram_method_with_retry_async
from worker import tasks
from worker.database import Database
from worker.main import app

logger = get_task_logger(__name__)
TMP_PATH = Path().cwd().joinpath("tmp")


def run_process_task(attachments: List):
    tasks.process_attachments.s(attachments=attachments).apply_async()


def show_progress(current, total):
    if total > 0:
        logger.debug(f"{current * 100 / total:.1f}%")


def is_image_file(attachment):
    return attachment["type"] == "photo" or (
        attachment["type"] == "document"
        and attachment["raw"]["mime_type"][:5] == "image"
    )


def is_audio_file(attachment):
    return (
        attachment["type"] == "audio"
        or attachment["type"] == "voice"
        or (
            attachment["type"] == "document"
            and attachment["raw"]["mime_type"][:5] == "audio"
        )
    )


async def download_file_from_telegram(
    tg_message_or_file_id: Union[str, pyrogram_types.Message],
    tmp_dir: str,
    tg_client: TelegramClient,
) -> Union[str, None]:
    try:
        return cast(
            Union[str, None],
            await run_pyrogram_method_with_retry_async(
                3,
                tg_client.download_media,
                tg_message_or_file_id,
                tmp_dir,
                progress=show_progress,
            ),
        )
    except Exception:
        logger.error(
            "Could not download media from Telegram API",
            exc_info=True,
        )
        return None


def bucket_name_from_attachment_type(
    attachment_type: str,
) -> str:
    return StorageBucketNames(attachment_type.replace("_", "-") + "s").value


def rmdir(directory):
    directory = Path(directory)

    if not directory.is_dir():
        return

    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()


class DownloadTask(celery.Task):
    def cleanup(self, task_id):
        rmdir(Path(TMP_PATH.joinpath(task_id)))

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.cleanup(task_id)

    def on_success(self, retval, task_id, args, kwargs):
        self.cleanup(task_id)


async def move_to_downloads_dir(
    attachment_type: str, file_name: str, file_path_source: str
) -> Path:
    download_dir = TMP_PATH.joinpath(
        "downloads", bucket_name_from_attachment_type(attachment_type)
    )
    download_dir.mkdir(parents=True, exist_ok=True)
    download_dir_with_slash = download_dir.as_posix() + "/"

    return Path(file_path_source).rename(
        download_dir_with_slash + file_name + Path(file_path_source).suffix
    )


async def download_message_attachments_async(
    task: celery.Task, client_id: str, message_ids: List[str]
) -> dict:
    if not client_id or not message_ids:
        raise ValueError("Invalid task arguments")

    if not settings.save_attachment_types:
        raise ValueError(
            "Trying to download message attachments, but list of file types is empty"
        )

    database = Database()
    downloaded_attachments = []

    # get client doc from database
    db_client_doc = database.clients.find_one(
        {
            "_id": PyObjectId(client_id),
            "is_active": True,
            "session_hash": {"$exists": True, "$ne": None},
        }
    )

    if (
        not db_client_doc
        or not hasattr(db_client_doc, "session_hash")
        or not db_client_doc.session_hash
    ):
        raise ValueError(
            f"Error getting client document ({client_id}) with valid session hash."
        )

    tg_client = TelegramClient(
        db_client_doc.session_hash,
        api_id=db_client_doc.api_id,
        api_hash=db_client_doc.api_hash,
        no_updates=True,
    )

    # create new temp dir to download files fo this session (directory name is task_id)
    session_dir = TMP_PATH.joinpath("sessions", task.request.id)
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_with_slash = session_dir.as_posix() + "/"
    save_count = 0

    # load list of messages from database
    db_messages = list(
        database.messages.find(
            {"_id": {"$in": message_ids}},
            {"_id": 1, "attachment": 1, "message_id": 1, "chat": 1, "language": 1},
        )
    )
    database.close()

    logger.info(f"Initializing Telegram client '{db_client_doc.title}'")

    async with tg_client:
        for message in db_messages:

            attachment = cast(dict, message.attachment)
            chat = cast(dict, message.chat)

            if (
                not attachment
                or attachment["type"] not in settings.save_attachment_types
            ):
                continue

            logger.info(f"Fetch fresh file references for message '{message.id}'")

            # get updated file id (because file references become outdated)
            try:
                tg_message = cast(
                    pyrogram_types.Message,
                    await run_pyrogram_method_with_retry_async(
                        3, tg_client.get_messages, chat["_id"], message.message_id
                    ),
                )
            except Exception:
                logger.error(
                    "Could not fetch message from Telegram API",
                    exc_info=True,
                )
                continue

            if isinstance(tg_message, list):
                tg_message = tg_message[0]

            try:
                users, parsed_message = Message.from_pyrogram_message(
                    tg_message, PyObjectId(client_id)
                )
            except ValueError:
                continue

            # use updated attachment
            attachment = parsed_message.dict().get("attachment", None)
            if not attachment:
                continue

            logger.info(f"Start downloading {attachment['type'].upper()}")

            file_path = await download_file_from_telegram(
                tg_message, session_dir_with_slash, tg_client
            )

            if not file_path:
                continue

            path_new = await move_to_downloads_dir(
                attachment["type"], attachment["raw"]["file_unique_id"], file_path
            )

            if not path_new:
                continue

            chat_language = (
                message.language
                if message.language
                else settings.ocr_asr_fallback_language
            )  # TODO: consider chat.language_other

            # gather meta data for further processing (storage, ocr, asr)
            downloaded_attachment = {
                "message_id": message.id,
                "file_name": path_new.name,
                "type": attachment["type"],
                "language": chat_language,
            }

            # text recognition (ocr) for all image files
            if settings.ocr_enabled and is_image_file(attachment):
                downloaded_attachment["action"] = "ocr"

            # speech recognition (asr) for all audio files
            if (
                settings.asr_enabled
                and settings.asr_language == chat_language
                and is_audio_file(attachment)
            ):
                downloaded_attachment["action"] = "asr"

            logger.info(f"Saved {attachment['type'].upper()} to '{path_new}'")

            # check if attachment has "thumbs" key and download thumbs
            # can be None
            if (
                attachment["type"] not in ["sticker", "animation"]
                and "thumbs" in attachment["raw"]
                and attachment["raw"]["thumbs"] is not None
            ):
                # only save one (smallest) thumbnail
                thumb = attachment["raw"]["thumbs"][0]

                logger.info("Downloading THUMBNAIL")
                thumb_file_path = await download_file_from_telegram(
                    thumb["file_id"], session_dir_with_slash, tg_client
                )

                if not thumb_file_path:
                    continue

                thumb_new_path = await move_to_downloads_dir(
                    "thumbnail", thumb["file_unique_id"], thumb_file_path
                )
                logger.info(f"Saved THUMBNAIL to '{thumb_new_path}'")
                downloaded_attachment["thumbnail"] = thumb_new_path.name

            save_count += 1
            downloaded_attachments.append(downloaded_attachment)

            logger.info(f"Downloaded {save_count}/{len(message_ids)} attachments")

        logger.info(f"Closing Telegram client '{tg_client}'")

    run_process_task(downloaded_attachments)  # upload to storate, ocr, asr etc.
    session_dir.rmdir()  # error when diretory is not empty

    return {"save_count": save_count}


@app.task(bind=True, name="files.download_message_attachments")
def download_message_attachments(
    self: celery.Task, client_id: str, message_ids: List[str]
) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        download_message_attachments_async(self, client_id, message_ids)
    )
