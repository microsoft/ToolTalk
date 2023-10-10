import logging
import time
from functools import wraps

import openai

logger = logging.getLogger(__name__)


def retry_on_limit(func, retries=5, wait=60):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except openai.error.RateLimitError as error:
                logger.info(str(error))
                time.sleep(wait)
        raise openai.error.RateLimitError
    return wrapper


openai_chat_completion = retry_on_limit(openai.ChatCompletion.create)
openai_completion = retry_on_limit(openai.Completion.create)
