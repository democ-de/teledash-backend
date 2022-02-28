import asyncio
import functools
import itertools
import time
from typing import Any, Callable, List, TypeVar, Union, cast

from pydantic import validator
from pyrogram.errors import (
    FloodTestPhoneWait,
    FloodWait,
    SlowmodeWait,
    TakeoutInitDelay,
    TwoFaConfirmWait,
)

AnyReturnType = TypeVar("AnyReturnType")


def flatten(list_of_lists: List[list]) -> list:
    return list(itertools.chain(*list_of_lists))


def rsetattr(obj, attr, val):
    """
    Set attributes via dot notation.
    Credits: https://stackoverflow.com/a/31174427/5732518
    """
    pre, _, post = attr.rpartition(".")
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj, attr, *args):
    """
    Get attributes via dot notation.
    Credits: https://stackoverflow.com/a/31174427/5732518
    """

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def serialize_pyrogram_type(v: Any) -> Union[dict, list, None]:
    exclude_keys = [
        "_client",
        "waveform",  # exclude "waveform" because not helpful bytes data
    ]

    if not v:
        return v

    def serialize(obj):
        if hasattr(obj, "__dict__"):
            return {
                key: serialize(value)
                for key, value in obj.__dict__.items()
                if key not in exclude_keys
            }
        elif isinstance(obj, list):
            return [serialize(o) for o in obj]

        return obj

    if isinstance(v, list):
        return [serialize(r) for r in v]

    return serialize(v)


def pyrogram_type_validator(*fields: str):
    # src: https://github.com/samuelcolvin/pydantic/discussions/2938
    return validator(*fields, allow_reuse=True)(serialize_pyrogram_type)


def run_pyrogram_method_with_retry(
    retries: int, func: Callable[..., AnyReturnType], *args, **kwargs
) -> Union[AnyReturnType, None]:
    for retry in range(retries):
        try:
            return func(*args, **kwargs)
        except (
            TwoFaConfirmWait,
            FloodTestPhoneWait,
            FloodWait,
            SlowmodeWait,
            TakeoutInitDelay,
        ) as e:
            # flood errors: https://docs.pyrogram.org/api/errors/flood
            # raise exception when last retry failed
            if retry == (retries - 1):
                raise e

            seconds = cast(int, e.x)  # e.x contains the flood wait timeout
            print(f"Flood exception. Waiting {seconds} seconds")
            time.sleep(seconds)


async def run_pyrogram_method_with_retry_async(
    retries: int, func: Callable[..., AnyReturnType], *args, **kwargs
) -> Union[AnyReturnType, None]:
    seconds = 10
    for retry in range(retries):
        try:
            return await func(*args, **kwargs)
        except (TimeoutError, OSError) as e:
            print(f"Waiting {seconds} seconds!")
            await asyncio.sleep(seconds)
            if retry == (retries - 1):
                print("Skipping!", e)
                raise e
        except (
            TwoFaConfirmWait,
            FloodTestPhoneWait,
            FloodWait,
            SlowmodeWait,
            TakeoutInitDelay,
        ) as e:
            # flood errors: https://docs.pyrogram.org/api/errors/flood
            # raise exception when last retry failed
            if retry == (retries - 1):
                raise e

            seconds = cast(int, e.x)  # e.x contains the flood wait timeout
            print(f"Flood exception. Waiting {seconds} seconds")
            await asyncio.sleep(seconds)
