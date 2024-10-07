import functools
import logging
import time
import inspect
import sys
from typing import Callable
from functools import wraps
from typing import Callable, Any, Type, Optional
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, status
import asyncio

import functools
import logging
import time
import asyncio
from typing import Callable, Any, Type, Optional, List, get_origin, get_args
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, status



def log_and_validate(
    logger: logging.Logger,
    validate_output: bool = False,
    output_model: Optional[Type[BaseModel]] = None,
):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            # Log the arguments
            args_repr = [repr(a)[:500] for a in args]
            kwargs_repr = [f"{k}={v!r}"[:500] for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.info(f"{func_name} called with args: {signature}")

            try:
                result = await func(*args, **kwargs)

                if validate_output and output_model:
                    validation_start = time.time()
                    try:
                        origin = get_origin(output_model)
                        if origin is list or origin is List:
                            # Validate each item in the list
                            item_model = get_args(output_model)[0]
                            for item in result:
                                item_model.model_validate(item)
                        elif issubclass(output_model, BaseModel):
                            output_model.model_validate(result)
                        else:
                            raise ValueError("Unsupported output_model type")

                        validation_time = time.time() - validation_start
                        logger.info(
                            f"{func_name}: Output validation successful. Time: {validation_time:.4f} seconds"
                        )
                    except ValidationError as ve:
                        logger.error(f"{func_name}: Output validation failed: {ve}")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Output validation failed",
                        ) from ve

                total_time = time.time() - start_time
                logger.info(
                    f"{func_name}: Function executed successfully. Total time: {total_time:.4f} seconds"
                )
                return result

            except HTTPException as http_exc:
                total_time = time.time() - start_time
                logger.error(
                    f"{func_name}: HTTP error: {http_exc.detail}. Status code: {http_exc.status_code}. Total time: {total_time:.4f} seconds"
                )
                raise http_exc

            except Exception as e:
                total_time = time.time() - start_time
                logger.exception(
                    f"{func_name}: Unexpected error: {str(e)}. Total time: {total_time:.4f} seconds"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {str(e)}",
                ) from e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            # Log the arguments
            args_repr = [repr(a)[:500] for a in args]
            kwargs_repr = [f"{k}={v!r}"[:500] for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.info(f"{func_name} called with args: {signature}")

            try:
                result = func(*args, **kwargs)

                if validate_output and output_model:
                    validation_start = time.time()
                    try:
                        origin = get_origin(output_model)
                        if origin is List:
                            # Validate each item in the list
                            item_model = get_args(output_model)[0]
                            for item in result:
                                item_model.model_validate(item)
                        elif issubclass(output_model, BaseModel):
                            output_model.model_validate(result)
                        else:
                            raise ValueError("Unsupported output_model type")

                        validation_time = time.time() - validation_start
                        logger.info(
                            f"{func_name}: Output validation successful. Time: {validation_time:.4f} seconds"
                        )
                    except ValidationError as ve:
                        logger.error(f"{func_name}: Output validation failed: {ve}")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Output validation failed",
                        ) from ve

                total_time = time.time() - start_time
                logger.info(
                    f"{func_name}: Function executed successfully. Total time: {total_time:.4f} seconds"
                )
                return result

            except HTTPException as http_exc:
                total_time = time.time() - start_time
                logger.error(
                    f"{func_name}: HTTP error: {http_exc.detail}. Status code: {http_exc.status_code}. Total time: {total_time:.4f} seconds"
                )
                raise http_exc

            except Exception as e:
                total_time = time.time() - start_time
                logger.exception(
                    f"{func_name}: Unexpected error: {str(e)}. Total time: {total_time:.4f} seconds"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {str(e)}",
                ) from e

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def create_log_and_validate_decorator(logger):
    def decorator_factory(validate_output=False):
        return log_and_validate(logger, validate_output=validate_output)

    return decorator_factory


def preserve_validate_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._is_decorated = True
    wrapper._validate_output = True
    return wrapper


def apply_decorator_to_module(logger):
    def wrapper(module):
        if isinstance(module, str):
            module_name = module
            module_obj = sys.modules[module]
        else:
            module_name = module.__name__
            module_obj = module

        for name, obj in inspect.getmembers(module_obj):
            if inspect.isfunction(obj) and obj.__module__ == module_name:
                # Check if the function is already decorated with preserve_validate_decorator
                if hasattr(obj, "_is_decorated") and obj._is_decorated:
                    if getattr(obj, "_validate_output", False):
                        continue  # Skip this function as it's already properly decorated

                # Determine whether to validate output
                validate_output = getattr(obj, "_validate_output", False)

                # Apply the log_and_validate decorator
                new_func = log_and_validate(logger, validate_output=validate_output)(
                    obj
                )

                # Preserve the _is_decorated and _validate_output attributes
                new_func._is_decorated = True
                new_func._validate_output = validate_output

                setattr(module_obj, name, new_func)

    return wrapper
