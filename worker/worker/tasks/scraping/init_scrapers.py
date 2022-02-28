from datetime import datetime, timedelta
from typing import Iterable, List, cast

from celery import group
from celery.utils.log import get_task_logger
from pyrogram import types as pyrogram_types
from pyrogram.client import Client as TelegramClient

from common.database.models.chat import ChatType
from common.database.models.refs import ChatRef
from common.settings import settings
from common.utils import flatten
from worker import tasks
from worker.database import Database
from worker.main import app

logger = get_task_logger(__name__)


ClientChatMap = List[tuple[str, set[int]]]


def exclude_duplicate_chat_ids(clients: ClientChatMap) -> ClientChatMap:
    """
    Make each client have a unique set of chat ids
    """
    if len(clients) <= 1:
        return clients

    # sort list, entry with most chat ids to the top
    clients.sort(key=lambda x: len(x[1]), reverse=True)

    # find duplicate chat ids and remove them
    for index, client in enumerate(clients):
        client_id, chat_ids = client
        duplicates = flatten(
            [
                [id for id in ch_ids if id in chat_ids]
                for cl_id, ch_ids in clients
                if cl_id != client_id
            ]
        )
        clients[index] = (client_id, {id for id in chat_ids if id not in duplicates})

    return clients


def get_active_tasks(task_names: List[str]):
    result = []
    for worker_name, worker_tasks in app.control.inspect().active().items():
        wanted_tasks = [task for task in worker_tasks if task["name"] in task_names]
        result.extend(wanted_tasks)

    return result


@app.task(name="scraping.init_scrapers")
def init_scrapers() -> None:
    database = Database()
    client_chat_map: ClientChatMap = []
    active_scraping_tasks = get_active_tasks(["scraping.scrape_chats"])
    active_client_ids: List[str] = [
        task["kwargs"]["client_id"]
        for task in active_scraping_tasks
        if "client_id" in task["kwargs"]
    ]
    active_chat_ids: List[int] = flatten(
        [
            task["kwargs"]["chat_ids"]
            for task in active_scraping_tasks
            if "chat_ids" in task["kwargs"]
        ]
    )

    # get all client documents and collect chat ids to scrape
    for client_doc in database.clients.find(
        {"is_active": True, "session_hash": {"$exists": True, "$ne": None}}
    ):
        if not hasattr(client_doc, "session_hash") or not client_doc.session_hash:
            logger.info(
                f'Skipping client "{client_doc.id}" because of missing session_hash.'
            )
            continue

        # exclude clients being scraped
        if str(client_doc.id) in active_client_ids:
            continue

        tg_client = TelegramClient(
            client_doc.session_hash,
            api_id=client_doc.api_id,
            api_hash=client_doc.api_hash,
            no_updates=True,
        )

        # loop client chats and create a map of client- and chat-ids
        with tg_client:
            # fetch chat ids for this client from the Telegram API
            chat_refs: List[dict] = [
                ChatRef.from_pyrogram_chat(dialog.chat).dict(
                    exclude_none=True, by_alias=True
                )
                for dialog in cast(
                    Iterable[pyrogram_types.Dialog], tg_client.iter_dialogs()
                )
                if dialog.chat.type
                in ChatType._value2member_map_  # skip unsupported chat types
            ]

        # update client doc with updated list of chat refs
        database.clients.update_one(
            {"_id": client_doc.id}, {"$set": {"chats": chat_refs}}
        )

        # exclude chat_ids being scraped
        tg_chat_ids: List[int] = [
            chat["_id"] for chat in chat_refs if chat["_id"] not in active_chat_ids
        ]
        if not tg_chat_ids:
            continue

        # exclude chat ids that have been scraped within
        # last minutes of scrape_chats_interval_minutes
        chat_ids_scraped_recently = [
            chat.id
            for chat in database.chats.find(
                {
                    "_id": {"$in": tg_chat_ids},
                    "scraped_at": {
                        "$gt": datetime.utcnow()
                        - timedelta(minutes=settings.scrape_chats_interval_minutes)
                    },
                },
                {"_id": 1},
            )
        ]
        if chat_ids_scraped_recently:
            tg_chat_ids = [
                chat_id
                for chat_id in tg_chat_ids
                if chat_id not in chat_ids_scraped_recently
            ]
            logger.warn(
                f"Skipping {len(chat_ids_scraped_recently)} chat(s) (recently scraped)"
            )

        if tg_chat_ids:
            client_chat_map.append((str(client_doc.id), set(tg_chat_ids)))

    # make all clients have a unique set of chat ids
    client_chat_map = exclude_duplicate_chat_ids(client_chat_map)

    # create subtasks and run in parallel
    jobs = group(
        [
            tasks.scrape_chats.s(client_id=client_id, chat_ids=list(chat_ids))
            for client_id, chat_ids in client_chat_map
            if chat_ids
        ]
    )

    if jobs:
        jobs.apply_async()
    else:
        logger.info("No scrapers started")

    # close db connection
    database.close()


# @worker_shutting_down.connect
# def worker_shutting_down_handler(sig, how, exitcode, ** kwargs):
#     print('Shutting down...')
