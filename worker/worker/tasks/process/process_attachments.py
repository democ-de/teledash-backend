from mimetypes import guess_type
from pathlib import Path
from typing import List

from celery.utils.log import get_task_logger
from minio.error import InvalidResponseError

from common.settings import settings
from common.storage import Storage, StorageBucketNames
from worker.database import Database
from worker.main import app
from worker.tasks.process.utils.speech_recognition import (
    load_model_speech_recognition,
    recognize_speech,
)
from worker.tasks.process.utils.text_recognition import recognize_text

logger = get_task_logger(__name__)
TMP_PATH = Path().cwd().joinpath("tmp")


def bucket_name_from_attachment_type(
    attachment_type: str,
) -> str:
    return StorageBucketNames(attachment_type.replace("_", "-") + "s").value


def upload_file_to_storage(
    file_path: str, bucket_name: str, object_name: str, storage: Storage
) -> bool:
    mime_type, encoding = guess_type(file_path)

    # upload to file storage
    try:
        storage.client.fput_object(
            bucket_name, object_name, file_path, content_type=mime_type
        )
    except FileNotFoundError:
        logger.error(f"File {file_path} not found", exc_info=True)
    except InvalidResponseError:
        logger.error("Error uploading file to storage", exc_info=True)
        return False

    return True


@app.task(name="process.process_attachments")
def process_attachments(attachments: List[dict]) -> dict:
    process_count = 0
    ocr_text = None
    asr_text = None
    model_asr = None

    storage = Storage()
    database = Database()

    # load asr model if needed
    if settings.asr_enabled and any(
        attachment.get("action", None) == "asr" for attachment in attachments
    ):
        logger.info("Loading speech recognition model")
        model_asr = load_model_speech_recognition(model_name=settings.asr_model_name)

    for attachment in attachments:
        bucket_name = bucket_name_from_attachment_type(attachment["type"])
        object_name = attachment["file_name"]
        file_path = TMP_PATH.joinpath(
            "downloads",
            bucket_name_from_attachment_type(attachment["type"]),
            object_name,
        )
        file_path_str = file_path.__str__()

        # TODO: fingerprint/hash files to detect duplicates

        # Note: file duplicates can exist but will be removed after the first upload
        if file_path.is_file():

            upload_file_to_storage(file_path_str, bucket_name, object_name, storage)

            logger.info(
                f"Uploaded {attachment['type'].upper()} to storage '{object_name}'"
            )

            # recognize text (ocr) in image files
            if "action" in attachment and attachment["action"] == "ocr":
                logger.info(f"Starting text recognition ({attachment['language']})")
                ocr_text = recognize_text(
                    image=file_path_str,
                    languages=[attachment["language"]],
                    model_type=settings.ocr_model_type,
                )

            # recognize speech (asr) in audio files
            if "action" in attachment and attachment["action"] == "asr" and model_asr:
                logger.info(f"Starting speech recognition '{attachment['language']}'")

                asr_text = recognize_speech(
                    audio=file_path_str,
                    model=model_asr,
                )
            try:
                file_path.unlink()
            except FileNotFoundError:
                logger.error(f"File {file_path} not found", exc_info=True)

        else:
            # TODO: Handle duplicates and fetch previous ocr/asr result
            logger.info(f"Skipping '{object_name}' (already uploaded)")

        # create storage reference
        storage_refs = [{"bucket": bucket_name, "object": object_name}]

        # check if attachment has "thumbs" key and download thumbnails
        # can be None
        if "thumbnail" in attachment:
            thumb_object_name = attachment["thumbnail"]
            thumb_file_path = TMP_PATH.joinpath(
                "downloads",
                "thumbnails",
                thumb_object_name,
            )

            if thumb_file_path.is_file():
                upload_file_to_storage(
                    thumb_file_path.__str__(),
                    "thumbnails",
                    thumb_object_name,
                    storage,
                )
                logger.info(f"Uploaded THUMBNAIL to storage '{thumb_object_name}'")

                try:
                    thumb_file_path.unlink()
                except FileNotFoundError:
                    logger.error(f"File {thumb_file_path} not found", exc_info=True)

            # update storage references with thumbnails
            storage_refs.append({"bucket": "thumbnails", "object": thumb_object_name})

        # save storage refs and ocr / asr (if available) in db
        save_data = {}
        save_data["attachment.storage_refs"] = storage_refs

        if ocr_text:
            save_data["attachment.ocr"] = ocr_text
        if asr_text:
            save_data["attachment.transcription"] = asr_text

        try:
            database.messages.update_one(
                {"_id": attachment["message_id"]},
                {"$set": save_data},
            )
        except Exception:
            logger.error(
                f"Couldn't update storage references for {attachment['message_id']}",
                exc_info=True,
            )

        process_count += 1
        logger.info(f"Processed {process_count}/{len(attachments)} attachments")

    return {"process_count": process_count}
