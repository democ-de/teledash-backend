from enum import Enum
from typing import Optional

from pydantic import BaseModel

from common.database.models.refs import UserRef


# Reference: https://docs.pyrogram.org/api/enums/MessageEntityType
class MessageEntityType(str, Enum):
    mention = "mention"
    hashtag = "hashtag"
    cashtag = "cashtag"
    bot_command = "bot_command"
    url = "url"
    email = "email"
    phone_number = "phone_number"
    bold = "bold"
    italic = "italic"
    underline = "underline"
    strikethrough = "strikethrough"
    spoiler = "spoiler"
    code = "code"
    pre = "pre"
    blockquote = "blockquote"
    text_link = "text_link"
    text_mention = "text_mention"
    bank_card = "bank_card"
    custom_emoji = "custom_emoji"
    unknown = "unknown"


# Reference: https://docs.pyrogram.org/api/types/MessageEntity
class MessageEntity(BaseModel):
    type: MessageEntityType
    offset: int
    length: int
    url: Optional[str]
    user: Optional[UserRef]
    language: Optional[str]
    custom_emoji_id: Optional[int]
