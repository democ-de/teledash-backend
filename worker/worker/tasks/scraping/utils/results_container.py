from typing import Callable, Dict, List, Literal

from celery.utils.log import get_task_logger
from pydantic.main import BaseModel
from pymongo.errors import BulkWriteError

from worker.database import Database

CollectionName = Literal["chats", "messages", "users", "metrics"]
ResultsContainerData = Dict[CollectionName, List[Dict]]


logger = get_task_logger(__name__)


class ResultsContainer:
    """
    Helper class to handle scraping results and perform database actions.
    """

    def __init__(
        self,
        size: int,
        keys: List[CollectionName],
        database: Database,
        generate_requests: Callable,
    ) -> None:
        self.size = size
        self.keys = keys
        self.data: ResultsContainerData = {}
        self.database = database
        self.generate_requests = generate_requests

        self.clear_data()

    def clear_data(self) -> None:
        self.data = {key: [] for key in self.keys}

    def add(self, key: CollectionName, model: BaseModel) -> None:
        self.data[key].append(
            # export model to dict
            model.dict(exclude_none=True, by_alias=True)
        )

    def has(self, key, attribute, value):
        if key in self.data:
            return any(
                item[attribute] == value for item in self.data[key] if attribute in item
            )
        else:
            return False

    def count(self) -> int:
        return sum(len(results) for results in self.data.values())

    @property
    def is_full(self) -> bool:
        return self.count() >= self.size

    def save_to_database(self) -> None:
        """
        Save documents to database. Count results of database transactions.
        """
        logger.info(f"Saving {self.count()} documents")

        for key, documents in self.data.items():
            if not documents:
                continue

            collection = getattr(self.database, key)
            requests = self.generate_requests(key, documents)

            try:
                collection.bulk_write(requests, ordered=False).bulk_api_result
            except BulkWriteError as bwe:
                # log errors other than duplicate key errors
                if any(e["code"] != 11000 for e in bwe.details["writeErrors"]):
                    logger.error("Error saving documents to database", exc_info=True)
                    raise bwe
