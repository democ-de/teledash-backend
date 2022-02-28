from typing import List, Optional, Tuple, Union, cast

from pydantic import BaseModel, ValidationError
from pyrogram import types as pyrogram_types

from common.database.models.pyobjectid import PyObjectId
from common.database.models.refs import UserRef
from common.database.models.user import User
from common.utils import serialize_pyrogram_type


class MessageServiceInfo(BaseModel):
    new_chat_members: Optional[List[UserRef]]
    left_chat_member: Optional[UserRef]
    new_chat_title: Optional[str]
    new_chat_photo: Optional[dict]  # TODO: pyrogram_types.Photo
    delete_chat_photo: Optional[bool]
    group_chat_created: Optional[bool]
    supergroup_chat_created: Optional[bool]
    channel_chat_created: Optional[bool]
    migrate_to_chat_id: Optional[int]
    migrate_from_chat_id: Optional[int]
    pinned_message_id: Optional[int]

    @classmethod
    def from_pyrogram_message(
        cls, message: pyrogram_types.Message, client_id: PyObjectId
    ) -> Tuple[List[User], Union["MessageServiceInfo", None]]:
        new_users = []
        wanted_attributes = [
            "new_chat_members",
            "left_chat_member",
            "new_chat_title",
            "new_chat_photo",
            "delete_chat_photo",
            "group_chat_created",
            "supergroup_chat_created",
            "channel_chat_created",
            "migrate_to_chat_id",
            "migrate_from_chat_id",
            "pinned_message",
        ]

        if message.service not in wanted_attributes:
            return [], None

        # parse service info users
        try:
            new_chat_members = (
                [
                    User.from_pyrogram_user(user, client_id)
                    for user in message.new_chat_members
                ]
                if message.new_chat_members
                else None
            )
            left_chat_member = (
                User.from_pyrogram_user(message.left_chat_member, client_id)
                if message.left_chat_member
                else None
            )
        except ValidationError:
            raise ValueError(
                f'Error validating users in service info ("{message.message_id}")'
            )

        if new_chat_members:
            new_users = new_chat_members

        if left_chat_member:
            new_users.append(left_chat_member)

        service_info = cls(
            new_chat_members=(
                [user.create_ref() for user in new_chat_members]
                if new_chat_members
                else None
            ),
            left_chat_member=(
                left_chat_member.create_ref() if left_chat_member else None
            ),
            new_chat_title=message.new_chat_title,
            new_chat_photo=cast(
                Union[None, dict], serialize_pyrogram_type(message.new_chat_photo)
            ),
            delete_chat_photo=message.delete_chat_photo,
            group_chat_created=message.group_chat_created,
            supergroup_chat_created=message.supergroup_chat_created,
            channel_chat_created=message.channel_chat_created,
            migrate_to_chat_id=message.migrate_to_chat_id,
            migrate_from_chat_id=message.migrate_from_chat_id,
            pinned_message_id=(
                message.pinned_message.message_id if message.pinned_message else None
            ),
        )

        return new_users, service_info
