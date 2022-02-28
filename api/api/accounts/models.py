from datetime import datetime
from typing import List, Optional

from fastapi_users import models
from pydantic import Field

from common.database.models.pyobjectid import PyObjectId


class Account(models.BaseUser):
    first_name: str
    last_name: str
    clients: Optional[List[PyObjectId]]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class AccountCreate(models.BaseUserCreate):
    first_name: str
    last_name: str


class AccountUpdate(models.BaseUserUpdate):
    first_name: Optional[str]
    last_name: Optional[str]


class AccountDB(Account, models.BaseUserDB):
    pass
