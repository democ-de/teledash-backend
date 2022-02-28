from enum import Enum
from typing import List, Optional, Union, cast

from pydantic import BaseModel
from pyrogram import types as pyrogram_types

from common.utils import serialize_pyrogram_type


class MessageAttachmentType(str, Enum):
    audio = "audio"
    document = "document"
    photo = "photo"
    sticker = "sticker"
    video = "video"
    animation = "animation"
    voice = "voice"
    video_note = "video_note"
    contact = "contact"
    location = "location"
    venue = "venue"
    poll = "poll"
    web_page = "web_page"
    dice = "dice"
    game = "game"


class MessageAttachmentStorageRef(BaseModel):
    bucket: str  # audios
    object: str  # asdoi32j4knmljasdasd.mp3


class MessageAttachment(BaseModel):
    type: MessageAttachmentType
    group_id: Optional[str]  # media group id
    # TODO: pyrogram types: Audio, Document, Photo, Sticker, Animation, Game, Video, Voice, VideoNote, Contact, Location, Venue, WebPage, Poll, Dice # noqa: E501
    raw: Optional[dict] = None
    ocr: Optional[str] = None
    transcription: Optional[str] = None
    storage_refs: Optional[List[MessageAttachmentStorageRef]] = None

    class Config:
        use_enum_values = True

    @classmethod
    def from_pyrogram_message(
        cls, message: pyrogram_types.Message
    ) -> Union["MessageAttachment", None]:
        """
        Parse Message attachment.
        A message object from Pyrogram (or Telegram API?) can only have one attachment.
        Other attachments belonging to the same message are part of other message
        objects and grouped by "media_group_id".
        """

        #
        media_attr = message.media
        if not media_attr:
            return None

        return cls(
            type=MessageAttachmentType(media_attr),
            group_id=message.media_group_id if message.media_group_id else None,
            raw=cast(dict, serialize_pyrogram_type(getattr(message, media_attr))),
        )
