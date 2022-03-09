from datetime import datetime, timedelta
from typing import Iterable, List, Tuple, Union, cast

import gcld3
from bson.objectid import ObjectId
from celery.utils.log import get_task_logger
from pydantic import ValidationError
from pymongo import InsertOne, ReplaceOne
from pyrogram import types as pyrogram_types
from pyrogram.client import Client as TelegramClient
from pyrogram.errors import exceptions

from common.database.models.chat import Chat, ChatMetrics, ChatType
from common.database.models.message import Message
from common.database.models.metric import Metric
from common.settings import settings
from common.utils import run_pyrogram_method_with_retry
from worker import tasks
from worker.aggregations import aggregate_metrics
from worker.database import Database
from worker.main import app

from .utils.results_container import ResultsContainer

logger = get_task_logger(__name__)
language_detector = None


def get_language_detector():
    global language_detector

    if language_detector is None:
        language_detector = gcld3.NNetLanguageIdentifier(  # type: ignore
            min_num_bytes=0, max_num_bytes=1000
        )

    return language_detector


def iter_history(
    tg_client: TelegramClient, chat_id: Union[int, str], reverse: bool = False
) -> Iterable[pyrogram_types.Message]:
    # copied from pyrogram iter_history()
    offset_id = 1 if reverse else 0
    current = 0
    total = (1 << 31) - 1

    while True:
        messages = cast(
            List[pyrogram_types.Message],
            tg_client.get_history(
                chat_id=chat_id, offset_id=offset_id, reverse=reverse
            ),
        )

        if not messages:
            return

        offset_id = messages[-1].message_id + (1 if reverse else 0)

        for message in messages:
            yield message

            current += 1

            if current >= total:
                return


def get_chat_language(
    chat_id: int, chat_doc: Union[Chat, None], tg_client: TelegramClient
) -> Tuple[Union[str, None], Union[List[str], None]]:
    language = getattr(chat_doc, "language", None)
    language_other = getattr(chat_doc, "language_other", None)

    if language:
        return language, language_other

    text_list = [
        msg.text
        for msg in cast(List[pyrogram_types.Message], tg_client.get_history(chat_id))
        # TODO: catch exceptions during get_history() e.g. TimeoutError
        if hasattr(msg, "text") and msg.text
    ]

    if not text_list:
        logger.warning(f'Could not detect language for chat "{chat_id}"')
        return None, None

    text_str = "\n".join(text_list)
    detector = get_language_detector()
    # supported lang codes by MongoDb
    # see https://docs.mongodb.com/manual/reference/text-search-languages/
    supported_lang_codes = (
        "da",
        "nl",
        "en",
        "fi",
        "fr",
        "de",
        "hu",
        "it",
        "nb",
        "pt",
        "ro",
        "ru",
        "es",
        "sv",
        "tr",
    )
    languages = [
        result.language
        for result in detector.FindTopNMostFreqLangs(text_str, num_langs=3)
        if result.is_reliable
    ]
    # save first language if supported by mongodb
    language = (
        languages[0] if languages and languages[0] in supported_lang_codes else None
    )
    # save secondary language and languages not supported by mongodb
    if language:
        language_other = languages[1:] if len(languages) > 1 else None
    else:
        language_other = languages if len(languages) >= 1 else None

    return language, language_other


def generate_requests(key, documents) -> List[Union[ReplaceOne, InsertOne]]:
    if key in ["messages", "metrics"]:
        return [InsertOne(doc) for doc in documents]
    elif key in ["users", "chats"]:
        return [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in documents]
    else:
        raise ValueError(f'No database action specified for key "{key}"')


def run_download_task(client_id: str, container: ResultsContainer):
    message_documents = container.data["messages"]
    if not message_documents:
        return

    oldest_message_date = (
        datetime.utcnow() - timedelta(days=settings.keep_attachment_files_days)
        if settings.keep_attachment_files_days > 0
        else datetime.min
    )
    wanted_file_types = settings.save_attachment_types

    def is_valid_message(msg):
        return (
            "date" in msg
            and msg["date"] > oldest_message_date
            and "attachment" in msg
            and msg["attachment"]["type"] in wanted_file_types
        )

    message_ids_with_attachments = [
        str(msg["_id"]) for msg in message_documents if is_valid_message(msg)
    ]

    if message_ids_with_attachments:
        tasks.download_message_attachments.s(
            client_id=client_id, message_ids=message_ids_with_attachments
        ).apply_async()


@app.task(name="scraping.scrape_chats")
def scrape_chats(client_id: str, chat_ids: List[int]) -> None:
    if not client_id or not chat_ids:
        raise ValueError("Invalid task arguments")

    database = Database()
    container = ResultsContainer(
        size=1000,
        keys=["users", "messages", "chats", "metrics"],
        database=database,
        generate_requests=generate_requests,
    )
    scrape_chats_max_days = settings.scrape_chats_max_days
    scrape_chats_max_date = (
        datetime.utcnow() - timedelta(days=scrape_chats_max_days)
        if scrape_chats_max_days > 0
        else datetime.min
    )

    # get client doc from database
    db_client_doc = database.clients.find_one(
        {
            "_id": ObjectId(client_id),
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

    # get chat documents for chat_ids
    db_chat_docs = {
        chat.id: chat
        for chat in database.chats.find(
            {"_id": {"$in": chat_ids}}, {"_id": 1, "language": 1, "language_other": 1}
        )
    }

    # init telegram client
    tg_client = TelegramClient(
        db_client_doc.session_hash,
        api_id=db_client_doc.api_id,
        api_hash=db_client_doc.api_hash,
        no_updates=True,
    )

    logger.info(f"Starting Telegram client {db_client_doc.title}")

    # scrape chats
    with tg_client:
        for tg_chat_id in chat_ids:
            try:
                # get chat info from Telegram API
                tg_chat = cast(
                    pyrogram_types.Chat,
                    run_pyrogram_method_with_retry(3, tg_client.get_chat, tg_chat_id),
                )
            except exceptions.PeerIdInvalid:
                logger.error(
                    f'Error getting chat info for chat "{tg_chat_id}" (PeerIdInvalid)'
                )
                continue
            except Exception:
                logger.error(
                    f'Error getting chat info for chat "{tg_chat_id}"', exc_info=True
                )
                continue

            # skip if chat is not of correct type
            if tg_chat.type not in ChatType._value2member_map_:
                continue

            try:
                # parse chat
                new_chat = Chat.from_pyrogram_chat(tg_chat, db_client_doc.id)
            except ValidationError:
                logger.error(f'Error validating chat "{tg_chat.id}"', exc_info=True)
                continue

            # create metrics for chat: members_count
            if new_chat.members_count is not None:
                try:
                    new_chat_metric = Metric.from_chat(new_chat)
                    container.add("metrics", new_chat_metric)
                except ValueError as e:
                    logger.error(
                        e,
                        exc_info=True,
                    )

            # aggregate activity (message_posted) for last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            activity_last_day = aggregate_metrics(
                database,
                {
                    "metadata.chat_id": new_chat.id,
                    "metadata.type": "message_posted",
                    "ts": {"$gte": yesterday},
                },
                "$sum",
            )

            # aggregate growth (members_count) for last 24 hours
            growth_last_day = aggregate_metrics(
                database,
                {
                    "metadata.chat_id": new_chat.id,
                    "metadata.type": "chat_members_count",
                    "ts": {"$gte": yesterday},
                },
                "$avg",
            )

            # TODO: Improve (won't consider the messages that are being scraped after)
            new_chat.metrics = ChatMetrics(
                activity_last_day=activity_last_day, growth_last_day=growth_last_day
            )

            # detect chat language
            chat_language, chat_languages_other = get_chat_language(
                tg_chat_id, db_chat_docs.get(tg_chat_id, None), tg_client
            )
            new_chat.language = chat_language
            new_chat.language_other = chat_languages_other

            container.add("chats", new_chat)

            # get id of last message in chat, if it exists in database
            latest_message = database.messages.find_one(
                {"chat._id": tg_chat.id}, sort=[("date", -1)]
            )
            last_message_id = latest_message.message_id if latest_message else None

            # get chat messages from Telegram API
            logger.info(
                f"Fetching messages for chat {tg_chat.id} (max_date: {scrape_chats_max_date}, last_message_id: {last_message_id})"  # noqa: E501
            )

            for message in iter_history(tg_client, tg_chat.id):
                if last_message_id is not None and message.message_id < last_message_id:
                    break

                if message.date:
                    message_date = datetime.utcfromtimestamp(message.date)
                    if message_date < scrape_chats_max_date:
                        break

                try:
                    # parse chat messages and containing users
                    new_users, new_message = Message.from_pyrogram_message(
                        message, db_client_doc.id, tg_chat
                    )
                except (ValidationError, ValueError):
                    logger.error(
                        f'Error validating message "{message.message_id}"',
                        exc_info=True,
                    )
                    continue

                # create metric for new message: message_posted
                try:
                    new_message_posted_metric = Metric.from_new_message_posted(
                        new_message
                    )
                    container.add("metrics", new_message_posted_metric)
                except ValueError as e:
                    logger.error(
                        e,
                        exc_info=True,
                    )

                # create metric for new message: views
                if new_message.views is not None:
                    try:
                        new_message_views_metric = Metric.from_new_message_views(
                            new_message
                        )
                        container.add("metrics", new_message_views_metric)
                    except ValueError as e:
                        logger.error(
                            e,
                            exc_info=True,
                        )

                # add chat language
                new_message.language = chat_language

                # save users and message
                [
                    container.add("users", user)
                    for user in new_users
                    if not container.has("users", "_id", user.id)
                ]
                container.add("messages", new_message)

                # update database
                if container.is_full:
                    container.save_to_database()
                    run_download_task(client_id, container)
                    container.clear_data()

    # Finally, insert remaining results (even though container limit is not reached)
    if container.count():
        container.save_to_database()
        run_download_task(client_id, container)

    database.close()
