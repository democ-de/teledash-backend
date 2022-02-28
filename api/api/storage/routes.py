from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from urllib3.response import HTTPResponse

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.storage import get_storage
from common.storage import Storage


def file_streamer(response):
    for d in response.stream(32 * 1024):
        yield d

    response.close()
    response.release_conn()


def get_storage_router(app):

    router = APIRouter()
    current_active_verified_user = get_current_active_verified_user()

    @router.get(
        "/storage/{bucket_name}/{object_name}",
        response_description="Get a file from storage",
        tags=["storage"],
        responses={
            404: {"description": "The bucket or file was not found."},
            400: {
                "description": "Any other error why the file could not be fetched.",
            },
            200: {
                "description": "Requested file from storage. Can be of any media type.",
                "content": {
                    "*/*": {},
                },
            },
        },
        response_class=StreamingResponse,
    )
    async def get_file(
        bucket_name: str,
        object_name: str,
        attachment: bool = False,
        account: Account = Depends(current_active_verified_user),
        storage: Storage = Depends(get_storage),
    ):
        try:
            response: HTTPResponse = storage.client.get_object(bucket_name, object_name)
            content_type = response.headers.get("content-type")
        except S3Error as e:
            # all S3Error codes:
            # https://github.com/minio/minio-go/blob/master/s3-error.go
            status_code = status.HTTP_400_BAD_REQUEST
            if e.code == "NoSuchBucket" or e.code == "NoSuchKey":
                status_code = status.HTTP_404_NOT_FOUND

            raise HTTPException(status_code, detail=e.message)
        except Exception as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

        return StreamingResponse(
            file_streamer(response),
            media_type=content_type,
            headers={
                "Content-Disposition": f'{"attachment; " if attachment else ""}filename={object_name}'  # noqa: E501
            },
        )

    return router
