import functools
import logging
import time
import inspect
import sys
from functools import wraps
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, status
import asyncio
from typing import Callable, Any, Type, Optional, List, get_origin, get_args

def format_type_info(type_info, indent=0):
    """Format type info in a readable hierarchical structure"""
    indent_str = "  " * indent
    
    # Base cases - handle primitive types and None
    if type_info is None:
        return "None"
        
    if not isinstance(type_info, dict):
        return str(type_info)
        
    # Handle dictionary type_info structure
    result = []
    type_name = type_info.get('type', 'unknown')
    result.append(type_name)
    
    # Add length if present
    if 'length' in type_info:
        result[-1] += f" ({type_info['length']} items)"
    
    # Handle fields
    fields = type_info.get('fields')
    if fields:
        if isinstance(fields, dict):
            result.append(f"{indent_str}  Fields:")
            for field, field_type in fields.items():
                formatted_type = format_type_info(field_type, indent + 2)
                result.append(f"{indent_str}    {field}: {formatted_type}")
        else:
            result.append(f"{indent_str}  Fields: {fields}")
    
    # Handle value types
    value_types = type_info.get('value_types')
    if value_types and isinstance(value_types, dict):
        result.append(f"{indent_str}  Values:")
        for key, value_type in value_types.items():
            formatted_type = format_type_info(value_type, indent + 2)
            result.append(f"{indent_str}    {key}: {formatted_type}")
    
    # Handle sample types
    sample_types = type_info.get('sample_types')
    if sample_types and isinstance(sample_types, (list, tuple)):
        result.append(f"{indent_str}  Sample types:")
        for sample in sample_types:
            formatted_type = format_type_info(sample, indent + 2)
            result.append(f"{indent_str}    - {formatted_type}")
    
    return "\n".join(result)


def get_detailed_type_info(obj, current_depth=0, max_depth=3):
    """Get detailed type information with special handling for Pydantic models"""
    if current_depth >= max_depth:
        return str(type(obj).__name__)
    
    if isinstance(obj, BaseModel):
        # Use Pydantic's model_json_schema for efficient schema extraction
        schema = obj.model_json_schema()
        return {
            'type': type(obj).__name__,
            'fields': {
                field: get_detailed_type_info(getattr(obj, field), current_depth + 1, max_depth)
                for field in obj.model_fields.keys()
            } if current_depth < max_depth - 1 else 'nested_fields'
        }
    
    if isinstance(obj, dict):
        return {
            'type': 'dict',
            'value_types': {
                k: get_detailed_type_info(v, current_depth + 1, max_depth)
                for k, v in list(obj.items())[:5]  # Limit to first 5 keys
            }
        }
    
    if isinstance(obj, (list, tuple, set)):
        container_type = type(obj).__name__
        if len(obj) == 0:
            return f"empty_{container_type}"
        
        # Sample first few elements
        sample_size = min(3, len(obj))
        samples = list(obj)[:sample_size]
        
        return {
            'type': container_type,
            'length': len(obj),
            'sample_types': [
                get_detailed_type_info(item, current_depth + 1, max_depth)
                for item in samples
            ]
        }
    
    # Handle common Python types with additional info
    if isinstance(obj, (int, float, str, bool)):
        return type(obj).__name__
    
    if obj is None:
        return 'None'
    
    # For other types, just return the type name
    return type(obj).__name__


def get_basic_type_info(obj):
    """Get basic type information without deep inspection"""
    if isinstance(obj, dict):
        return f"dict[{len(obj)} keys]"
    elif isinstance(obj, (list, tuple)):
        return f"{type(obj).__name__}[{len(obj)} items]"
    elif isinstance(obj, BaseModel):
        return f"{type(obj).__name__}[Pydantic]"
    else:
        return type(obj).__name__

def log_and_validate(
    logger: logging.Logger,
    validate_output: bool = False,
    output_model: Optional[Type[BaseModel]] = None,
):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            wrapper_start = time.time()
            
            # Pre-execution logging
            args_repr = [repr(a)[:500] for a in args]
            kwargs_repr = [f"{k}={v!r}"[:500] for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.info(f"{func.__name__} called with args: {signature}")
            
            pre_exec_time = time.time()
            overhead = pre_exec_time - wrapper_start
            
            try:
                # Core function execution timing
                func_start = time.time()
                result = await func(*args, **kwargs)
                func_end = time.time()
                func_time = func_end - func_start
                
                # Post-execution operations timing
                post_start = time.time()
                
                # Type info logging
                type_info = get_detailed_type_info(result)
                
                # Validation if needed
                if validate_output and output_model:
                    try:
                        origin = get_origin(output_model)
                        if origin is list or origin is List:
                            item_model = get_args(output_model)[0]
                            for item in result:
                                item_model.model_validate(item)
                        elif issubclass(output_model, BaseModel):
                            output_model.model_validate(result)
                        else:
                            raise ValueError("Unsupported output_model type")
                    except ValidationError as ve:
                        logger.error(f"{func.__name__}: Output validation failed: {ve}")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Output validation failed",
                        ) from ve
                
                post_end = time.time()
                post_overhead = post_end - post_start
                total_overhead = overhead + post_overhead
                total_time = post_end - wrapper_start
                
                # Timing breakdown logging
                logger.info(
                    f"{func.__name__} execution details:\n"
                    f"Timing:\n"
                    f"  - Core function execution: {func_time:.4f}s\n"
                    f"  - Logging/validation overhead: {total_overhead:.4f}s\n"
                    f"  - Total time: {total_time:.4f}s\n"
                    # f"Return type structure:\n"
                    # f"{format_type_info(type_info)}"
                )
                
                return result

            except Exception as e:
                error_time = time.time()
                total_time = error_time - wrapper_start
                logger.exception(
                    f"{func.__name__}: Error after {total_time:.4f}s: {str(e)}"
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            wrapper_start = time.time()
            
            # Pre-execution logging
            args_repr = [repr(a)[:500] for a in args]
            kwargs_repr = [f"{k}={v!r}"[:500] for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.info(f"{func.__name__} called with args: {signature}")
            
            pre_exec_time = time.time()
            overhead = pre_exec_time - wrapper_start
            
            try:
                # Core function execution timing
                func_start = time.time()
                result = func(*args, **kwargs)
                func_end = time.time()
                func_time = func_end - func_start
                
                # Post-execution operations timing
                post_start = time.time()
                
                # Type info logging
                type_info = get_detailed_type_info(result)
                
                # Validation if needed
                if validate_output and output_model:
                    try:
                        origin = get_origin(output_model)
                        if origin is list or origin is List:
                            item_model = get_args(output_model)[0]
                            for item in result:
                                item_model.model_validate(item)
                        elif issubclass(output_model, BaseModel):
                            output_model.model_validate(result)
                        else:
                            raise ValueError("Unsupported output_model type")
                    except ValidationError as ve:
                        logger.error(f"{func.__name__}: Output validation failed: {ve}")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Output validation failed",
                        ) from ve
                
                post_end = time.time()
                post_overhead = post_end - post_start
                total_overhead = overhead + post_overhead
                total_time = post_end - wrapper_start
                
                # Timing breakdown logging
                logger.info(
                    f"{func.__name__} execution details:\n"
                    f"Timing:\n"
                    f"  - Core function execution: {func_time:.4f}s\n"
                    f"  - Logging/validation overhead: {total_overhead:.4f}s\n"
                    f"  - Total time: {total_time:.4f}s\n"
                    # f"Return type structure:\n"
                    # f"{format_type_info(type_info)}"
                )
                
                return result

            except Exception as e:
                error_time = time.time()
                total_time = error_time - wrapper_start
                logger.exception(
                    f"{func.__name__}: Error after {total_time:.4f}s: {str(e)}"
                )
                raise

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
