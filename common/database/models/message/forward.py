from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pyrogram import types as pyrogram_types

from common.database.models.refs import ChatRef, UserRef


class MessageForward(BaseModel):
    from_user: Optional[UserRef]
    sender_name: Optional[str]
    from_chat: Optional[ChatRef]
    from_message_id: Optional[int]
    signature: Optional[str]
    date: Optional[datetime]

    @classmethod
    def from_pyrogram_message(cls, message: pyrogram_types.Message) -> "MessageForward":
        return cls(
            from_user=(
                UserRef.from_pyrogram_user(message.forward_from)
                if message.forward_from
                else None
            ),
            sender_name=message.forward_sender_name,
            from_chat=(
                ChatRef.from_pyrogram_chat(message.forward_from_chat)
                if message.forward_from_chat
                else None
            ),
            from_message_id=message.forward_from_message_id,
            signature=message.forward_signature,
            date=(
                datetime.fromtimestamp(message.forward_date)
                if message.forward_date
                else None
            ),
        )
