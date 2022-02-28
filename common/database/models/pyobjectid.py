from bson.errors import InvalidId
from bson.objectid import ObjectId

# source/discussion:
# https://github.com/tiangolo/fastapi/issues/68
# https://www.mongodb.com/developer/quickstart/python-quickstart-fastapi/


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return cls(v)
        except InvalidId:
            raise ValueError("Not a valid ObjectId")

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")
