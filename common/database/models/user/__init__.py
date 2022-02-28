from datetime import datetime
from typing import List, Optional, Union, cast

from pydantic import BaseModel, Field
from pyrogram import types as pyrogram_types

from common.database.models.aggregations import AggregatedMetrics
from common.database.models.pyobjectid import PyObjectId
from common.database.models.refs import ChatRef, UserRef
from common.utils import serialize_pyrogram_type


class UserMetrics(BaseModel):
    activity_last_day: Optional[AggregatedMetrics] = None
    activity_total: Optional[AggregatedMetrics] = None


class UserIn(BaseModel):
    """
    The user model (a Telegram user) with only those fields that can be modified by
    a client consuming the API (used in REST-API for POST/PUT/PATCH endpoints).

    Adapted from Pyrograms user model:
    https://docs.pyrogram.org/api/types/User#pyrogram.types.User
    """


class User(UserIn):
    """
    The complete user model (a Telegram user) as it is stored in the database (used in
    REST-API and by the scraper).

    Adapted from Pyrograms user model:
    https://docs.pyrogram.org/api/types/User#pyrogram.types.User
    """

    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_self: Optional[bool]
    is_contact: Optional[bool]
    is_mutual_contact: Optional[bool]
    is_deleted: Optional[bool]
    is_bot: Optional[bool]
    is_verified: Optional[bool]
    is_restricted: Optional[bool]
    is_scam: Optional[bool]
    is_fake: Optional[bool]
    is_support: Optional[bool]
    metrics: Optional[UserMetrics] = None
    status: Optional[str]
    last_online_date: Optional[datetime]
    next_offline_date: Optional[datetime]
    language_code: Optional[str]
    dc_id: Optional[int]
    phone_number: Optional[str]
    photo: Optional[dict]  # TODO: pyrogram_types.ChatPhoto
    restrictions: Optional[List[dict]]  # TODO: pyrogram_types.Restriction
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_by: PyObjectId
    in_chats: Optional[List[ChatRef]] = None

    class Config:
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        arbitrary_types_allowed = True  # required PyObjectId
        json_encoders = {PyObjectId: str}

    def create_ref(self) -> UserRef:
        return UserRef(
            id=self.id,
            username=self.username,
            first_name=self.first_name,
            last_name=self.last_name,
        )

    @classmethod
    def from_pyrogram_user(
        cls, user: pyrogram_types.User, client_id: PyObjectId
    ) -> "User":
        datetime_now = datetime.utcnow()

        return cls(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_self=user.is_self,
            is_contact=user.is_contact,
            is_mutual_contact=user.is_mutual_contact,
            is_deleted=user.is_deleted,
            is_bot=user.is_bot,
            is_verified=user.is_verified,
            is_restricted=user.is_restricted,
            is_scam=user.is_scam,
            is_fake=user.is_fake,
            is_support=user.is_support,
            status=user.status,
            last_online_date=(
                datetime.fromtimestamp(user.last_online_date)
                if user.last_online_date
                else None
            ),
            next_offline_date=(
                datetime.fromtimestamp(user.next_offline_date)
                if user.next_offline_date
                else None
            ),
            language_code=user.language_code,
            dc_id=user.dc_id,
            phone_number=user.phone_number,
            photo=cast(Union[dict, None], serialize_pyrogram_type(user.photo)),
            restrictions=cast(
                Union[list, None], serialize_pyrogram_type(user.restrictions)
            ),
            updated_at=datetime_now,
            scraped_by=client_id,
        )


class UserOut(User):
    """
    The complete user model as it is returned by the REST-API.
    All fields are optional.
    """

    id: Optional[int] = None
    scraped_by: Optional[PyObjectId] = None
    metrics: Optional[UserMetrics] = None
