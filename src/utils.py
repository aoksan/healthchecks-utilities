# src/utils.py
import time
import functools
from .logger import debug

def time_it(func):
    """
    A decorator that logs the execution time of a function at the DEBUG level.
    """
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        # Call the original function
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration = end_time - start_time
        # Use the function's name in the log message for clarity
        debug(f"The '{func.__name__}' function took {duration:.2f} seconds to complete.")
        return value
    return wrapper_timer
