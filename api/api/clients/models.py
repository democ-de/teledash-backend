from typing import Any

from pydantic import BaseModel

from common.database.models.client import Client


class ClientCreateSession(BaseModel):
    phone_code_hash: str
    phone_code: str

    class Config:
        schema_extra = {
            "example": {
                "phone_code_hash": "f00a1d1bcbfd3aee00",
                "phone_code": "12345",
            }
        }


class ClientCreate(Client):
    auth: Any  # TODO: Improve typing
