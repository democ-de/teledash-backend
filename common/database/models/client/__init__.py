from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from common.database.models.pyobjectid import PyObjectId
from common.database.models.refs import ChatRef


class ClientIn(BaseModel):
    """
    The client model with Telegram auth infos and only those fields that can be
    modified by a client consuming the API (used in REST-API for
    POST/PUT/PATCH endpoints).
    """

    title: Optional[str]
    phone_number: str
    api_id: int
    api_hash: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True  # required PyObjectId
        json_encoders = {PyObjectId: str}


class Client(ClientIn):
    """
    The complete client model with Telegram auth infos as it is stored in the
    database (used in REST-API and by the scraper).
    """

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_hash: Optional[str]
    user_id: Optional[int]  # Associated Telegram User
    # List of Telegram chats (channels, groups etc.)
    chats: Optional[List[ChatRef]]
    is_active: bool = False
    # Should be read-only after create
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClientOut(Client):
    """
    The complete client model as it is returned by the REST-API.
    All fields are optional.
    """

    id: Optional[PyObjectId] = None
    is_active: Optional[bool] = None
