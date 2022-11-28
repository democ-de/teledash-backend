from typing import List, Literal

from pydantic import BaseSettings, validator

from common.database.models.message.attachment import MessageAttachmentType


class Settings(BaseSettings):
    # MongoDB
    mongo_host: str
    mongo_user: str
    mongo_password: str
    mongo_db_name: str

    # Storage
    storage_endpoint: str
    storage_access_key: str
    storage_secret_key: str

    # Flower
    flower_host: str
    flower_port: int
    flower_user: str
    flower_password: str

    # Scraping settings
    scrape_chats_max_days: int
    scrape_chats_interval_minutes: int
    save_attachment_types: List[str]
    keep_attachment_files_days: int

    # JWT
    jwt_secret: str
    jwt_lifetime_seconds: int

    # Language (for OCR and ASR)
    ocr_asr_fallback_language: str

    # OCR
    ocr_enabled: bool
    ocr_model_type: Literal["fast", "best", "custom"]

    # ASR
    asr_enabled: bool
    asr_language: str
    asr_model_name: str

    # API
    api_allow_origins: List[str]

    @validator("save_attachment_types")
    def match_attachment_type(cls, v):
        allowed_types = MessageAttachmentType._member_names_
        if any(t not in allowed_types for t in v):
            raise ValueError(
                '"SAVE_ATTACHMENT_TYPES" contains invalid attachment type(s)'
            )
        return v


settings = Settings()  # type: ignore
