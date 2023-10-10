import copy
import re
from datetime import datetime
from typing import Optional

from .exceptions import APIException
from .api import API, APISuite
from .utils import semantic_str_compare

MESSAGE_DB_NAME = "Message"
"""
message database schema:

username: str - key
messages: List[dict]
    message_id: str
    timestamp: str
    sender: str
    message: str
"""


class SearchMessages(API):
    description = "Searches messages matching filters returning 5 most recent results."
    parameters = {
        "session_token": {
            'type': "string",
            'description': 'The session_token of the user.',
            'required': True
        },
        "query": {
            "type": "string",
            "description": "Query containing keywords to search for.",
            "required": False
        },
        "match_type": {
            "type": "string",
            "enum": ["any", "all"],
            "description": "Whether to match any or all keywords. Defaults to any.",
            "required": False
        },
        "sender": {
            'type': "string",
            'description': 'Username of the sender.',
            "required": False
        },
        "start_date": {
            'type': "string",
            'description': 'Starting time to search for, in the pattern of %Y-%m-%d %H:%M:%S.',
            "required": False
        },
        "end_date": {
            'type': "string",
            'description': 'End time to search for, in the pattern of %Y-%m-%d %H:%M:%S.',
            "required": False
        },
    }
    output = {
        "messages": {
            'type': 'array',
            "item": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "sender": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
            'description': 'list of messages matching search criteria.'
        },
    }
    is_action = False
    database_name = MESSAGE_DB_NAME

    def call(
            self,
            session_token: str,
            query: Optional[str] = None,
            match_type: Optional[str] = "any",
            sender: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> dict:
        user_info = self.check_session_token(session_token)
        username = user_info['username']
        if username not in self.database:
            return {"messages": []}

        user_messages = self.database[username]
        if query is None and sender is None and start_date is None and end_date is None:
            raise APIException('At least one of query, sender, start_date, end_date must be provided.')

        if match_type not in ["any", "all"]:
            raise APIException('match_type must be either "any" or "all".')

        if start_date is not None:
            start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        if end_date is not None:
            end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        if start_date is not None and end_date is not None and start_date > end_date:
            raise APIException('Start date must be earlier than end date.')

        keywords = query.lower().split() if query else None
        matched_messages = []
        for message in user_messages.values():
            message_date = datetime.strptime(message['timestamp'], '%Y-%m-%d %H:%M:%S')
            if self.now_timestamp < message_date:
                # ignore "future" messages
                continue
            if sender is not None and sender != message['sender']:
                continue
            if start_date is not None and start_date > message_date:
                continue
            if end_date is not None and end_date < message_date:
                continue
            # skip if doesn't match any keywords
            if keywords is not None:
                keyword_matches = [keyword in message['message'].lower() for keyword in keywords]
                matches_keyword = any(keyword_matches) if match_type == "any" else all(keyword_matches)
                if not matches_keyword:
                    continue
            matched_messages.append(message)

        matched_messages.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'), reverse=True)
        matched_messages = matched_messages[:5]
        matched_messages = copy.deepcopy(matched_messages)
        return {"messages": matched_messages}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        if prediction["exception"] != ground_truth["exception"]:
            return False
        predict_token = prediction["request"]["parameters"]["session_token"]
        ground_truth_token = ground_truth["request"]["parameters"]["session_token"]
        if predict_token != ground_truth_token:
            return False

        # as long as ground_truth emails are contained in response emails, it's correct
        response_ids = {message["message_id"] for message in prediction['response']['messages']}
        ground_truth_messages = ground_truth['response']['messages']
        for message in ground_truth_messages:
            if message["message_id"] not in response_ids:
                return False
        return True


class SendMessage(API):
    description = 'Sends a message to another user.'
    parameters = {
        "session_token": {
            'type': "string",
            'description': 'The session_token of the user.',
            "required": True
        },
        "receiver": {
            'type': "string",
            'description': 'The receiver\'s username.',
            "required": True
        },
        "message": {
            'type': "string",
            'description': 'The message.',
            "required": True
        },
    }
    output = {
        "message_id": {
            'type': "string",
            'description': 'message_id on success.'
        },
    }
    is_action = True

    def call(self, session_token: str, receiver: str, message: str) -> dict:
        self.check_session_token(session_token)
        # accept all receivers since they could resolve
        if message == "":
            raise APIException("Message cannot be empty.")
        message_id = f"{self.random.randint(0, 0xffffffff):08x}-{self.random.randint(0, 0xffffffff):08x}"
        return {"message_id": message_id}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """Don't really care about response message id"""
        if prediction['exception'] != ground_truth['exception']:
            return False

        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]

        # parameters besides message must be the same
        if predict_params["session_token"] != ground_truth_params["session_token"]:
            return False
        if predict_params['receiver'] != predict_params['receiver']:
            return False

        # messages must be relatively the same
        if semantic_str_compare(predict_params["message"], ground_truth_params["message"]) < 0.8:
            return False
        return True


class MessagesSuite(APISuite):
    name = 'Messages'
    description = 'This API lets a user send and search messages.'
    apis = [SendMessage, SearchMessages]
