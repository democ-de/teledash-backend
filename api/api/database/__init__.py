from api.database.client import Database

database = Database(connect=False)


async def get_database() -> Database:
    return database
