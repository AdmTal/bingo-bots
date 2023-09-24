import time
from functools import wraps


class TimeIt:
    def __init__(self):
        self.total_time = 0
        self.call_count = 0

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            result = func(*args, **kwargs)

            end_time = time.time()
            elapsed_time = end_time - start_time
            self.total_time += elapsed_time
            self.call_count += 1
            average_time = self.total_time / self.call_count
            print(
                f"{func.__name__} took {elapsed_time:.4f} seconds -- avg = {average_time:.4f} over {self.call_count} call(s)")
            return result

        return wrapper
