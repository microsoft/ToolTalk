import logging

from paper.evaluation import DATABASE_PATH
from paper.evaluation.tool_executor import ToolExecutor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    prediction = {
         "request": {
             "api_name": "CreateEvent",
             "parameters": {
                 "session_token": "98a5a87a-7714-b404",
                 "name": "walk",
                 "event_type": "event",
                 "description": "Taking a walk",
                 "start_time": "2023-09-11 13:20:00",
                 "end_time": "2023-09-11 14:20:00"
             }
         },
         "response": {
             "event_id": "e149636f-d9ca"
         },
         "exception": None,
         "role": "api",
         "match": False,
         "bad_action": True
    }

    ground_truth = {
        "request": {
            "api_name": "CreateEvent",
            "parameters": {
                "session_token": "98a5a87a-7714-b404",
                "name": "Walk",
                "event_type": "event",
                "start_time": "2023-09-11 13:20:00",
                "end_time": "2023-09-11 14:20:00"
            }
        },
        "response": {
            "event_id": "e149636f-d9ca"
        },
        "exception": None
    }

    tool_executor = ToolExecutor(init_database_dir=DATABASE_PATH)
    is_match = tool_executor.compare_api_calls(prediction, ground_truth)
    logger.debug(f"Is match: {is_match}")
    print(is_match)
