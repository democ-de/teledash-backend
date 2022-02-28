from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, cast

from pydantic import BaseModel, Field
from pyrogram import types as pyrogram_types

from common.database.models.aggregations import AggregatedMetrics
from common.database.models.pyobjectid import PyObjectId
from common.database.models.refs import ChatRef, MessageRef, UserRef
from common.utils import serialize_pyrogram_type

"""
Adapted from Pyrograms chat model:
https://docs.pyrogram.org/api/types/Chat#pyrogram.types.Chat
"""


class GlobalMetrics(BaseModel):
    users_count: Optional[int] = None
    chats_count: Optional[int] = None
    messages_count: Optional[int] = None
    photos_count: Optional[int] = None
    videos_count: Optional[int] = None
    voices_count: Optional[int] = None
    growth_total: Optional[AggregatedMetrics] = None
    activity_total: Optional[AggregatedMetrics] = None


class ChatMetrics(BaseModel):
    activity_last_day: Optional[AggregatedMetrics] = None
    activity_total: Optional[AggregatedMetrics] = None
    growth_last_day: Optional[AggregatedMetrics] = None
    growth_total: Optional[AggregatedMetrics] = None


class ChatType(str, Enum):
    # we don't save "bot" or "private" chats
    group = "group"
    supergroup = "supergroup"
    channel = "channel"


class ChatIn(BaseModel):
    """
    The chat model with only those fields that can be modified by a client consuming
    the API (used in REST-API for POST/PUT/PATCH endpoints).
    """

    language: Optional[str] = None
    language_other: Optional[List[str]] = None


class Chat(ChatIn):
    """
    The complete chat model as it is stored in the database (used by the scraper).
    """

    id: int
    type: ChatType  # group, supergroup or channel
    title: Optional[str]
    username: Optional[str]
    # TODO: is_active / exclude to manually disable scraping of specific chat
    is_verified: Optional[bool]
    is_restricted: Optional[bool]
    is_scam: Optional[bool]
    is_fake: Optional[bool]
    photo: Optional[dict]  # TODO: pyrogram_types.ChatPhoto
    description: Optional[str]
    invite_link: Optional[str]
    pinned_message: Optional[MessageRef]
    members: Optional[List[UserRef]] = None
    members_count: Optional[int]
    metrics: Optional[ChatMetrics] = None
    linked_chat: Optional[ChatRef]
    restrictions: Optional[List[dict]]  # TODO: pyrogram_types.Restriction
    permissions: Optional[dict]  # TODO: pyrogram_types.Restriction
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_at: datetime
    scraped_by: PyObjectId

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        arbitrary_types_allowed = True  # required PyObjectId
        json_encoders = {PyObjectId: str}

    def create_ref(self) -> ChatRef:
        return ChatRef(
            id=self.id,
            title=self.title,
            username=self.username,
        )

    @classmethod
    def from_pyrogram_chat(
        cls, tg_chat: pyrogram_types.Chat, client_id: PyObjectId
    ) -> "Chat":
        datetime_now = datetime.utcnow()

        return cls(
            id=tg_chat.id,
            type=ChatType(tg_chat.type),
            title=tg_chat.title,
            username=tg_chat.username,
            is_verified=tg_chat.is_verified,
            is_restricted=tg_chat.is_restricted,
            is_scam=tg_chat.is_scam,
            is_fake=tg_chat.is_fake,
            photo=cast(Union[dict, None], serialize_pyrogram_type(tg_chat.photo)),
            description=tg_chat.description,
            invite_link=tg_chat.invite_link,
            pinned_message=(
                MessageRef.from_pyrogram_message(tg_chat.pinned_message)
                if tg_chat.pinned_message
                else None
            ),
            members_count=tg_chat.members_count,
            linked_chat=(
                ChatRef.from_pyrogram_chat(tg_chat.linked_chat)
                if tg_chat.linked_chat
                else None
            ),
            restrictions=cast(
                Union[list, None], serialize_pyrogram_type(tg_chat.restrictions)
            ),
            permissions=cast(
                Union[dict, None], serialize_pyrogram_type(tg_chat.permissions)
            ),
            updated_at=datetime_now,
            scraped_at=datetime_now,
            scraped_by=client_id,
        )


class ChatOut(Chat):
    """
    The complete chat model as it is returned by the REST-API.
    All fields are optional.
    """

    id: Optional[int] = None
    type: Optional[ChatType] = None
    scraped_at: Optional[datetime] = None
    scraped_by: Optional[PyObjectId] = None
    metrics: Optional[ChatMetrics]
