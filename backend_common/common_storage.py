import logging
import uuid
from datetime import datetime, date
from typing import Any, Dict, Tuple, Optional, Union, List
import json
import os
import asyncio
import aiofiles
from contextlib import asynccontextmanager
from fastapi import HTTPException, status
from pydantic import BaseModel

from backend_common.common_config import CONF
from backend_common.logging_wrapper import apply_decorator_to_module

from backend_common.logger import logging

logger = logging.getLogger(__name__)





class FileLock:
    def __init__(self):
        self.locks = {}

    @asynccontextmanager
    async def acquire(self, filename):
        if filename not in self.locks:
            self.locks[filename] = asyncio.Lock()
        async with self.locks[filename]:
            yield


file_lock_manager = FileLock()


def to_serializable(obj: Any) -> Any:
    """
    Convert a Pydantic model or any other object to a JSON-serializable format.

    Args:
    obj (Any): The object to convert.

    Returns:
    Any: A JSON-serializable representation of the object.
    """
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(to_serializable(item) for item in obj)
    elif isinstance(obj, BaseModel):
        return to_serializable(obj.dict(by_alias=True))
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return to_serializable(obj.__dict__)
    else:
        return obj


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable format and verify serializability.

    Args:
    obj (Any): The object to convert.

    Returns:
    Any: A JSON-serializable representation of the object.

    Raises:
    ValueError: If the object cannot be serialized to JSON.
    """
    try:
        serializable_obj = to_serializable(obj)
        json.dumps(serializable_obj)
        return serializable_obj
    except (TypeError, OverflowError, ValueError) as e:
        raise ValueError(f"Object is not JSON serializable: {str(e)}")


async def use_json(
    file_path: str, mode: str, json_content: dict = None
) -> Optional[dict]:
    async with file_lock_manager.acquire(file_path):
        if mode == "w":
            try:
                async with aiofiles.open(file_path, mode="w") as file:
                    await file.write(json.dumps(json_content, indent=2))
            except IOError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error writing data file",
                )

        elif mode == "r":
            try:
                if os.path.exists(file_path):
                    async with aiofiles.open(file_path, mode="r") as file:
                        content = await file.read()
                        return json.loads(content)
                return None
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error parsing data file",
                )
            except IOError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error reading data file",
                )
        else:
            raise ValueError("Invalid mode. Use 'r' for read or 'w' for write.")


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
