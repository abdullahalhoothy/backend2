import json
import uuid
from pydantic import ValidationError
from fastapi import HTTPException, status
from typing import TypeVar, Optional, Type, Callable, Awaitable, Any
from pydantic import BaseModel
from backend_common.logging_wrapper import log_and_validate
import logging


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


@log_and_validate(logger)
async def request_handling(
    req: Optional[T],
    input_type: Optional[Type[T]],
    output_type: Optional[Type[U]],
    custom_function: Optional[Callable[..., Awaitable[Any]]],
    output: Optional[T] = "",
    wrap_output: bool = False
):
    if req and input_type:
        try:
            input_type.model_validate(req)
        except ValidationError as e:
            # You can customize the error response format
            validation_errors = e.errors()
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Validation failed",
                    "errors": validation_errors
                }
            )

    if custom_function is not None:
        try:
            if req:
                output = await custom_function(req=req)
            else:
                output = await custom_function()
        except HTTPException:
            # If it's already an HTTPException, just re-raise it
            raise
        except Exception as e:
            # For any other type of exception, wrap it in an HTTPException
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}",
            ) from e
    if wrap_output:
        output = {
            'data': output,
            'message': 'Request received.',
            'request_id': "req-" + str(uuid.uuid4())
        }
    res_body = output_type(**output) if output_type else output

    return res_body
