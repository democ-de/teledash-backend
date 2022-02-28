from typing import Iterator, List, cast

from celery.utils.log import get_task_logger
from pymongo.operations import ReplaceOne
from pyrogram import types as pyrogram_types
from pyrogram.client import Client as TelegramClient

from common.database.models.pyobjectid import PyObjectId
from common.database.models.user import User
from worker.database import Database
from worker.main import app
from worker.tasks.scraping.utils.results_container import ResultsContainer

logger = get_task_logger(__name__)


def get_chat_members(
    chat_id: int, client_id: PyObjectId, tg_client: TelegramClient
) -> List[User]:
    # TODO: returns currently max. 10.000 members
    # TODO: catch exceptions like timeouts
    # TODO: save status of users (admin, member, restricted, banned etc.)
    return [
        User.from_pyrogram_user(member.user, client_id)
        for member in cast(
            Iterator[pyrogram_types.ChatMember],
            tg_client.iter_chat_members(
                chat_id,
                filter="all",  # default: recent
            ),
        )
    ]


def generate_requests(key, documents) -> List[ReplaceOne]:
    return [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in documents]


@app.task(name="scraping.scrape_chat_members")
def scrape_chat_members() -> None:
    database = Database()
    container = ResultsContainer(
        size=1000,
        keys=["users"],
        database=database,
        generate_requests=generate_requests,
    )

    # get all client documents and collect chat ids to scrape
    client_docs = list(
        database.clients.find(
            {"is_active": True, "session_hash": {"$exists": True, "$ne": None}}
        )
    )

    for client_doc in client_docs:
        if not hasattr(client_doc, "session_hash") or not client_doc.session_hash:
            logger.info(
                f'Skipping client "{client_doc.id}" because of missing session_hash.'
            )
            continue

        # continue if client has not chat refs yet
        if not client_doc.chats:
            continue

        tg_client = TelegramClient(
            client_doc.session_hash,
            api_id=client_doc.api_id,
            api_hash=client_doc.api_hash,
            no_updates=True,
        )

        # Get chat ids from client doc
        chat_ids = [chat_ref["_id"] for chat_ref in cast(List[dict], client_doc.chats)]

        # Get chat docs from chat ids
        chat_docs = list(
            database.chats.find(
                {"_id": {"$in": chat_ids}, "type": {"$in": ["group", "supergroup"]}},
                {"_id": 1},
            )
        )

        logger.info(f"Initializing Telegram client '{tg_client}'")

        with tg_client:
            # loop chat docs and get chat members
            # save member/user refs in chat document
            for chat in chat_docs:
                logger.info(f"Fetching users for chat {chat.id}")

                chat_users = get_chat_members(chat.id, client_doc.id, tg_client)
                chat_user_refs: List[dict] = [
                    user.create_ref().dict(
                        exclude_none=True,
                    )
                    for user in chat_users
                ]

                logger.info(f"Collected {len(chat_user_refs)} users")

                # update chat doc now
                database.chats.update_one(
                    {"_id": chat.id},
                    {
                        "$set": {
                            "members": chat_user_refs,
                            # "members_count": len(chat_user_refs), # TODO: Fix
                        }
                    },
                )

                # store user in memory and save later
                [
                    container.add("users", user)
                    for user in chat_users
                    if not container.has("users", "_id", user.id)
                ]

                if container.is_full:
                    container.save_to_database()
                    container.clear_data()

    if container.count():
        container.save_to_database()

    database.close()
