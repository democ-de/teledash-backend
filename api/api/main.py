import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.accounts.auth import init_fast_api_users
from api.accounts.routes import get_accounts_router
from api.chats.routes import get_chats_router
from api.clients.routes import get_clients_router
from api.database import database
from api.messages.routes import get_messages_router
from api.metrics.routes import get_metrics_router
from api.storage import storage
from api.storage.routes import get_storage_router
from api.users.routes import get_users_router
from common.settings import settings

app = FastAPI(title="Teledash API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def configure_db_and_routes():
    database.connect()

    init_fast_api_users()
    app.include_router(get_accounts_router(app))
    app.include_router(get_messages_router(app))
    app.include_router(get_clients_router(app))
    app.include_router(get_chats_router(app))
    app.include_router(get_users_router(app))
    app.include_router(get_metrics_router(app))

    if settings.storage_endpoint and len(settings.save_attachment_types) >= 1:
        storage.connect()
        app.include_router(get_storage_router(app))


@app.on_event("shutdown")
async def shutdown_db_client():
    database.close()


@app.get("/")
async def root():
    return {"message": "Welcome"}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", reload=True, port=8000)
