from datetime import datetime
from typing import List, Optional, Tuple, Union, cast

from pydantic import BaseModel, Field
from pyrogram import types as pyrogram_types

from common.database.models.message.attachment import MessageAttachment
from common.database.models.message.forward import MessageForward
from common.database.models.message.service_info import MessageServiceInfo
from common.database.models.pyobjectid import PyObjectId
from common.database.models.refs import ChatRef, MessageRef, UserRef
from common.database.models.user import User
from common.utils import serialize_pyrogram_type


class MessageIn(BaseModel):
    """
    The message model with only those fields that can be modified by a client consuming
    the API (used in REST-API for POST/PUT/PATCH endpoints).

    Adapted from Pyrograms message model:
    https://docs.pyrogram.org/api/types/Message#pyrogram.types.Message
    """

    """
    partial index draft:
    {
        customFilter:
            {
                attachment: {$exists: true},
                'processed.attachment.ocr': {$exists: true},
                'processed.attachment.transcription': {$exists: true},
                'processed.attachment.in_storage': {$exists: true},
                'processed.text.translation': {$exists: true},
                'processed.caption.translation': {$exists: true},
            }
        }
    }


    """

    language: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        arbitrary_types_allowed = True  # required PyObjectId
        json_encoders = {PyObjectId: str}


class Message(MessageIn):
    """
    The complete message model as it is stored in the database (used in REST-API
    and by the scraper).

    Adapted from Pyrograms message model:
    https://docs.pyrogram.org/api/types/Message#pyrogram.types.Message
    """

    id: str  # a string created from chat-id and message-id
    # incrementing number in chat (only unique in combination with chat-id)
    message_id: int
    from_user: Optional[UserRef]
    chat: ChatRef
    sender_chat: Optional[ChatRef]
    date: Optional[datetime]
    forward: Optional[MessageForward]
    reply_to_message: Optional[MessageRef]
    mentioned: Optional[bool]
    is_empty: Optional[bool]
    attachment: Optional[MessageAttachment]
    edit_date: Optional[datetime]
    author_signature: Optional[str]
    text: Optional[str]
    entities: Optional[List[dict]]  # TODO: pyrogram_types.MessageEntity
    caption: Optional[str]
    caption_entities: Optional[List[dict]]  # TODO: pyrogram_types.MessageEntity
    views: Optional[int]
    is_outgoing: Optional[bool]
    service_info: Optional[MessageServiceInfo]
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_by: PyObjectId

    @staticmethod
    def create_message_id(message_id: int, chat_id: int) -> str:
        return f"{chat_id}:{message_id}"

    @classmethod
    def from_pyrogram_message(
        cls,
        tg_message: pyrogram_types.Message,
        client_id: PyObjectId,
        tg_chat: Optional[pyrogram_types.Chat] = None,
    ) -> Tuple[List[User], "Message"]:
        datetime_now = datetime.utcnow()
        chat = tg_message.chat if tg_message.chat else tg_chat

        if not chat:
            raise ValueError("Could not parse Message because of missing chat info")

        # parse user from message
        new_users: List[User] = []
        from_user: Union[User, None] = (
            User.from_pyrogram_user(tg_message.from_user, client_id)
            if tg_message.from_user
            else None
        )

        # parse sender user
        if from_user:
            new_users.append(from_user)

        # parse message forward
        wanted_attributes = [
            "forward_from",
            "forward_sender_name",
            "forward_from_chat",
            "forward_from_message_id",
            "forward_signature",
            "forward_date",
        ]
        has_wanted_attributes = any(
            getattr(tg_message, attr, None) is not None for attr in wanted_attributes
        )
        forward = (
            MessageForward.from_pyrogram_message(tg_message)
            if has_wanted_attributes
            else None
        )

        attachment = MessageAttachment.from_pyrogram_message(tg_message)

        service_info_users, service_info = MessageServiceInfo.from_pyrogram_message(
            tg_message, client_id
        )
        if service_info_users:
            new_users.extend(service_info_users)

        new_message = cls(
            id=cls.create_message_id(tg_message.message_id, chat.id),
            message_id=tg_message.message_id,
            from_user=from_user.create_ref() if from_user else None,
            sender_chat=(
                ChatRef.from_pyrogram_chat(tg_message.sender_chat)
                if tg_message.sender_chat
                else None
            ),
            date=datetime.fromtimestamp(tg_message.date) if tg_message.date else None,
            chat=ChatRef.from_pyrogram_chat(chat),
            forward=forward,
            reply_to_message=(
                MessageRef.from_pyrogram_message(tg_message.reply_to_message, chat)
                if tg_message.reply_to_message
                else None
            ),
            mentioned=tg_message.mentioned,
            is_empty=tg_message.empty,
            attachment=attachment,
            edit_date=(
                datetime.fromtimestamp(tg_message.edit_date)
                if tg_message.edit_date
                else None
            ),
            author_signature=tg_message.author_signature,
            text=tg_message.text,
            entities=cast(List[dict], serialize_pyrogram_type(tg_message.entities)),
            caption=tg_message.caption,
            caption_entities=cast(
                List[dict], serialize_pyrogram_type(tg_message.caption_entities)
            ),
            views=tg_message.views,
            is_outgoing=tg_message.outgoing,
            service_info=service_info,
            updated_at=datetime_now,
            scraped_by=client_id,
        )

        return new_users, new_message


class MessageOut(Message):
    """
    The complete message model as it is returned by the REST-API.
    All fields are optional.
    """

    id: Optional[str] = None
    message_id: Optional[int] = None
    chat: Optional[ChatRef] = None
    scraped_by: Optional[PyObjectId] = None
