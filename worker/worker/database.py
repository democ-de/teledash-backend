from typing import Dict, Generic, Iterator, Type, TypeVar, Union

from pymongo import MongoClient
from pymongo.database import Collection as PyMongoCollection
from pymongo.database import Database as PyMongoDatabase
from pymongo.results import BulkWriteResult, InsertOneResult, UpdateResult

from common.database.models.chat import Chat
from common.database.models.client import Client
from common.database.models.message import Message
from common.database.models.metric import Metric
from common.database.models.user import User
from common.settings import settings

T = TypeVar("T", Client, Chat, Message, User, Metric)


class Collection(Generic[T]):
    # src: https://stackoverflow.com/a/68819695/5732518
    name: str
    model: Type[T]

    def __init__(self, db: PyMongoDatabase) -> None:
        self.db = db
        self.collection: PyMongoCollection = getattr(self.db, self.name)

        if not self.model or not self.name:
            raise Exception(
                "Error initializing collection. Name or model not provided."
            )

    def __transform_document(self, doc) -> T:
        # convert "_id"-attribute to "id"
        if "_id" in doc.keys():
            doc["id"] = doc["_id"]
            del doc["_id"]

        return self.model.construct(**doc)

    def find_one(self, *args, **kwargs) -> Union[T, None]:
        doc = self.collection.find_one(*args, **kwargs)

        if not doc:
            return None

        return self.__transform_document(doc)

    def find(self, *args, **kwargs) -> Iterator[T]:
        for doc in self.collection.find(*args, **kwargs):
            yield self.__transform_document(doc)

    def aggregate(self, *args, **kwargs) -> Iterator[Dict]:
        for doc in self.collection.aggregate(*args, **kwargs):
            yield doc

    def update_one(self, *args, **kwargs) -> UpdateResult:
        return self.collection.update_one(*args, **kwargs)

    def bulk_write(self, *args, **kwargs) -> BulkWriteResult:
        return self.collection.bulk_write(*args, **kwargs)

    def insert_one(self, *args, **kwargs) -> InsertOneResult:
        return self.collection.insert_one(*args, **kwargs)


class ClientsCollection(Collection[Client]):
    name = "clients"
    model = Client


class ChatsCollection(Collection[Chat]):
    name = "chats"
    model = Chat


class MessagesCollection(Collection[Message]):
    name = "messages"
    model = Message


class UsersCollection(Collection[User]):
    name = "users"
    model = User


class MetricsCollection(Collection[Metric]):
    name = "metrics"
    model = Metric


class Database:
    def __init__(self, connect=True) -> None:
        if connect:
            self.connect()

    def connect(self) -> None:
        self.__client = MongoClient(
            host=settings.mongo_host,
            username=settings.mongo_user,
            password=settings.mongo_password,
        )
        self.__db = self.__get_database()

        # collections:
        self.clients = ClientsCollection(self.__db)
        self.chats = ChatsCollection(self.__db)
        self.messages = MessagesCollection(self.__db)
        self.users = UsersCollection(self.__db)
        self.metrics = MetricsCollection(self.__db)

    def __get_database(self) -> PyMongoDatabase:
        return self.__client[settings.mongo_db_name]

    def close(self):
        self.__client.close()
