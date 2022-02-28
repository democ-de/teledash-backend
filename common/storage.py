from enum import Enum

from minio import Minio
from minio.error import S3Error

from common.settings import settings


class StorageBucketNames(str, Enum):
    thumbnails = "thumbnails"  # One size of a photo or a file/sticker thumbnail.
    photos = "photos"  # photo files
    audios = "audios"  # audio files to be treated as music by the Telegram clients.
    documents = "documents"  # generic file, can be mp3, pdf etc.)
    animations = "animations"  # GIF or H.264/MPEG-4 AVC video without sound
    videos = "videos"  # video files
    voices = "voices"  # voice note (audio)
    video_notes = "video-notes"  # video note files (video)
    stickers = "stickers"  # sticker files (images)


class Storage:
    def __init__(self, connect=True) -> None:
        if connect is True:
            self.connect()

    def connect(self):
        self.client = Minio(
            settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=False,
        )

        # Create buckets if they don't exist.
        buckets = [member.value for member in StorageBucketNames._member_map_.values()]

        try:
            for bucket in buckets:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
        except S3Error as e:
            if e.code != "BucketAlreadyOwnedByYou":
                raise e


if __name__ == "__main__":
    storage = Storage()
