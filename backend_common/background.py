# my_middle_API/backend_common/background.py
from fastapi import BackgroundTasks
from contextvars import ContextVar
import time
from functools import wraps
import logging

background_tasks_context: ContextVar[BackgroundTasks] = ContextVar("background_tasks")


logger = logging.getLogger(__name__)


def wrap_task_with_logging(func, parent_func_name=None):
    if hasattr(func, '_is_wrapped_with_logging'):
        return func
        
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = f"{parent_func_name}::{func.__name__}" if parent_func_name else func.__name__

        args_repr = [repr(a)[:500] for a in args]
        kwargs_repr = [f"{k}={v!r}"[:500] for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        
        try:
            result = await func(*args, **kwargs)
            total_time = time.time() - start_time
            logger.info(f"Background task {func_name} completed with args: {signature}. Time: {total_time:.4f}s")
            return result
        except Exception as e:
            total_time = time.time() - start_time
            logger.exception(f"Background task {func_name} failed with args: {signature} after {total_time:.4f}s: {str(e)}")
            
    wrapper._is_wrapped_with_logging = True
    return wrapper

def get_background_tasks() -> BackgroundTasks:
    try:
        tasks = background_tasks_context.get()
        
        if not hasattr(tasks, '_patched_for_logging'):
            original_add_task = tasks.add_task
            
            def add_task_with_logging(func, *args, **kwargs):
                # Get the name of the function that's adding the background task
                import inspect
                frame = inspect.currentframe()
                caller_frame = frame.f_back
                parent_func_name = caller_frame.f_code.co_name
                
                wrapped_func = wrap_task_with_logging(func, parent_func_name)
                return original_add_task(wrapped_func, *args, **kwargs)
                
            tasks.add_task = add_task_with_logging
            tasks._patched_for_logging = True
            
        return tasks
    except LookupError:
        raise RuntimeError("BackgroundTasks not initialized in context")

def set_background_tasks(tasks: BackgroundTasks):
    background_tasks_context.set(tasks)
