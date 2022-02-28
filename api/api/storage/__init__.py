
from common.storage import Storage

storage = Storage(connect=False)


def get_storage() -> Storage:
    return storage
