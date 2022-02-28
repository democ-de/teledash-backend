from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from api.accounts.auth import get_current_active_verified_user
from api.accounts.models import Account
from api.clients.authenticator import TelegramAuthenticator, get_authenticator
from api.clients.models import ClientCreate, ClientCreateSession
from api.clients.validators import parse_client_filter, parse_client_sort
from api.database import get_database
from api.database.client import Database
from api.pagination import PaginatedClients, Pagination
from api.validators import parse_projection_params, parse_search_params
from common.database.models.client import ClientIn, ClientOut
from common.database.models.pyobjectid import PyObjectId


def get_clients_router(app):

    router = APIRouter()
    current_active_verified_user = get_current_active_verified_user()
    pagination = Pagination(maximum_limit=100)

    @router.get(
        "/clients",
        response_description="List all clients",
        tags=["clients"],
        response_model=PaginatedClients,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def list_clients(
        filter: dict = Depends(parse_client_filter),
        sort: dict = Depends(parse_client_sort),
        search: dict = Depends(parse_search_params),
        projection: dict = Depends(parse_projection_params),
        pagination: Tuple[int, int, int] = Depends(pagination.parse_params),
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        offset, limit, max_limit = pagination

        if search:
            filter.update(search)

        result = [
            doc
            async for doc in database.clients.find(
                filter,
                projection=projection,
                skip=offset,
                limit=limit,
                sort=sort,
            )
        ]

        return PaginatedClients.create(data=result, params=pagination)

    @app.post(
        "/clients",
        response_description="Create a new client",
        tags=["clients"],
        response_model=ClientCreate,
        status_code=status.HTTP_201_CREATED,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def create_client(
        client: ClientIn,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
        tg_auth: TelegramAuthenticator = Depends(get_authenticator),
    ):
        new_client_id = PyObjectId()

        try:
            auth = await tg_auth.start_auth(
                client_id=str(new_client_id),
                api_id=client.api_id,
                api_hash=client.api_hash,
                phone_number=client.phone_number,
                test_mode=False,
            )
        except Exception as e:
            # TODO: use logger
            print(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client could not be created",
            )

        client_dict = client.dict(exclude_none=True, by_alias=True)
        client_dict["_id"] = new_client_id

        repsonse = await database.clients.insert_one(client_dict)

        if not repsonse.acknowledged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client could not be created",
            )

        # Info: Authentication data will be returned but won't be stored in DB.
        client_dict["auth"] = auth

        return ClientCreate(**client_dict)

    @router.put(
        "/clients/{id}/session",
        response_description="Create a new client session",
        tags=["clients"],
        response_model=ClientOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def create_session(
        id: PyObjectId,
        session: ClientCreateSession,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
        tg_auth: TelegramAuthenticator = Depends(get_authenticator),
    ):
        client_doc = await database.clients.find_one({"_id": id})

        if not client_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with id {id} not found",
            )

        try:
            auth = await tg_auth.signin(
                client_id=str(id),
                phone_number=client_doc.phone_number,
                phone_code_hash=session.phone_code_hash,
                phone_code=session.phone_code,
            )
        except Exception as e:
            # TODO: use logger
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Client could not be authenticated",
            )

        client_doc.session_hash = auth["session_hash"]
        client_doc.user_id = auth["user"]["id"]

        response = await database.clients.update_one(
            {"_id": id}, {"$set": client_doc.dict(by_alias=True)}
        )

        if response.modified_count == 1:
            return client_doc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Client {id} could not be authenticated",
        )

    @app.get(
        "/clients/{id}",
        response_description="Get a single client",
        tags=["clients"],
        response_model=ClientOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def get_client(
        id: PyObjectId,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        client_doc = await database.clients.find_one({"_id": id})

        if not client_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return client_doc

    @router.put(
        "/clients/{id}",
        response_description="Update a client",
        tags=["clients"],
        response_model=ClientOut,
        response_model_exclude_none=True,
        response_model_exclude_unset=True,
    )
    async def update_client(
        id: PyObjectId,
        client: ClientIn,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        response = await database.clients.update_one(
            {"_id": id},
            {"$set": client.dict(exclude_unset=True, exclude_none=True, by_alias=True)},
        )

        if response.modified_count == 1:
            return await database.clients.find_one({"_id": id})

        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=f"Client with id {id} was not updated",
        )

    @app.delete(
        "/clients/{id}",
        response_description="Delete a client",
        tags=["clients"],
    )
    async def delete_client(
        id: PyObjectId,
        account: Account = Depends(current_active_verified_user),
        database: Database = Depends(get_database),
    ):
        response = await database.clients.delete_one({"_id": id})

        if response.deleted_count == 1:
            return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {id} not found",
        )

    return router
