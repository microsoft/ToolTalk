import copy
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List

from .exceptions import APIException
from .api import API, APISuite
from .utils import semantic_str_compare

logger = logging.getLogger(__name__)

"""
Database definition:

username: str - key
events: list of events

event: dict
    event_id: str - key
    name: str
    event_type: str
    description: str
    start_time: datetime
    end_time: datetime
    location: str - optional
    attendees: list(str) - optional
"""

CALENDAR_DB_NAME = "Calendar"


@dataclass(frozen=True)
class _EventTypes:
    MEETING: str = 'meeting'
    EVENT: str = 'event'


EventTypes = _EventTypes()


class CreateEvent(API):
    description = "Adds events to a user's calendar."
    parameters = {
        'session_token': {
            'type': "string",
            'description': "User's session_token.",
            "required": True
        },
        'name': {
            'type': "string",
            "enum": ['meeting', 'event'],
            'description': 'The name of the event.',
            "required": True
        },
        "event_type": {
            "type": "string",
            "description": "The type of the event, either 'meeting', 'event', or 'reminder.",
            "required": True,
        },
        "description": {
            "type": "string",
            "description": "The description of the event, no more than 1024 characters.",
            "required": False,
        },
        'start_time': {
            'type': "string",
            'description': 'The start time of the event, in the pattern of %Y-%m-%d %H:%M:%S',
            "required": True
        },
        'end_time': {
            'type': "string",
            'description': 'The end time of the event, in the pattern of %Y-%m-%d %H:%M:%S.',
            "required": True
        },
        'location': {
            'type': "string",
            'description': 'Optional, the location where the event is to be held.',
            "required": False,
        },
        'attendees': {
            "type": "array",
            "items": {"type": "string"},
            'description': 'The attendees as an array of usernames. Required if event type is meeting.',
            "required": False,
        }
    }
    output = {
        'event_id': {
            'type': "string",
            'description': 'event id on success. None on failure.',
        }
    }

    database_name = CALENDAR_DB_NAME
    is_action = True

    def call(
            self,
            session_token: str,
            name: str,
            event_type: str,
            start_time: str,
            end_time: str,
            description: str = None,
            location: str = None,
            attendees: List[str] = None,
    ) -> dict:
        if event_type not in asdict(EventTypes).values():
            raise APIException(f"Event type {event_type} not supported.")
        if event_type == EventTypes.MEETING and not attendees:
            raise APIException("Meeting must have attendees.")

        user_info = self.check_session_token(session_token)
        username = user_info["username"]

        # validate dates
        start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        if start_datetime > end_datetime:
            raise APIException("Start time must be before end time.")
        if start_datetime < self.now_timestamp or end_datetime < self.now_timestamp:
            raise APIException("Start time and end time must be in the future.")

        if attendees is not None:
            if username not in attendees:
                # add self, don't modify list externally
                attendees = attendees + [username]

        event_id = f"{self.random.randint(0, 0xffffffff):08x}-{self.random.randint(0, 0xffff):04x}"
        event = {
            "event_id": event_id,
            "name": name,
            "event_type": event_type,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "attendees": attendees,
        }
        if username not in self.database:
            self.database[username] = dict()
        self.database[username][event_id] = event
        return {"event_id": event["event_id"]}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """
        Check all required values. Also make sure no exception is thrown.
        Returned event_id is irrelevant.
        """
        if prediction["exception"] != ground_truth["exception"]:
            return False

        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]

        for key, value in ground_truth_params.items():
            # all included values in ground truth are necessary
            if key not in predict_params:
                logger.debug(f"Key {key} not found in prediction parameters.")
                return False

            predict_value = predict_params[key]
            if predict_value is None:
                logger.debug(f"Key {key} has None value in prediction parameters.")
                return False
            elif key in {"name", "description", "location"}:
                score = semantic_str_compare(value, predict_value)
                if score < 0.9:
                    logger.debug(f"Key {key} has low semantic similarity score of {score}.")
                    return False
            elif value != predict_value:
                logger.debug(f"Key {key} has different value {predict_value} != {value}.")
                return False

        return True


class DeleteEvent(API):
    description = "Deletes events from a user's calendar."
    parameters = {
        'session_token': {
            'type': "string",
            'description': "User's session_token.",
            "required": True
        },
        'event_id': {
            'type': "string",
            'description': 'The id of the event to be deleted.',
            "required": True
        }
    }
    output = {
        'status': {'type': "string", 'description': 'success or failed'}
    }

    database_name = CALENDAR_DB_NAME
    is_action = True

    def call(self, session_token: str, event_id: str) -> dict:
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if username not in self.database:
            raise APIException(f"Event {event_id} not found.")
        if event_id not in self.database[username]:
            raise APIException(f"Event {event_id} not found.")
        del self.database[username][event_id]
        return {"status": "success"}


class ModifyEvent(API):
    description = "Allows modification of an existing event."
    parameters = {
        'session_token': {
            'type': "string",
            'description': "User's session_token.",
            "required": True
        },
        "event_id": {
            "type": "string",
            "description": "The id of the event to be modified.",
            "required": True
        },
        "new_name": {
            "type": "string",
            "description": "The new name of the event.",
            "required": False
        },
        "new_start_time": {
            "type": "string",
            "description": "The new start time of the event.",
            "required": False
        },
        "new_end_time": {
            "type": "string",
            "description": "The new end time of the event. Required if new_start_time is provided.",
            "required": False
        },
        "new_description": {
            "type": "string",
            "description": "The new description of the event.",
            "required": False
        },
        "new_location": {
            "type": "string",
            "description": "The new location of the event.",
            "required": False
        },
        "new_attendees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The new attendees of the event. Array of usernames.",
            "required": False
        }
    }
    output = {
        'status': {'type': "string", 'description': 'success or failed'}
    }

    database_name = CALENDAR_DB_NAME
    is_action = True

    def call(
            self,
            session_token: str,
            event_id: str,
            new_name: str = None,
            new_start_time: str = None,
            new_end_time: str = None,
            new_description: str = None,
            new_location: str = None,
            new_attendees: list = None
    ) -> dict:
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if username not in self.database:
            raise APIException(f"Event {event_id} not found.")
        if event_id not in self.database[username]:
            raise APIException(f"Event {event_id} not found.")
        event = self.database[username][event_id]
        if new_name is not None:
            event["name"] = new_name
        if new_start_time is not None:
            if new_end_time is None:
                raise APIException("new_end_time must be provided if new_start_time is provided.")
            # validate new start and end times
            new_start_datetime = datetime.strptime(new_start_time, '%Y-%m-%d %H:%M:%S')
            new_end_datetime = datetime.strptime(new_end_time, "%Y-%m-%d %H:%M:%S")
            if new_start_datetime > new_end_datetime:
                raise APIException("Start time must be before end time.")
            if new_start_datetime < self.now_timestamp or new_end_datetime < self.now_timestamp:
                raise APIException("Start time and end time must be in the future.")

            event["start_time"] = new_start_time
        if new_end_time is not None:
            if new_start_time is None:
                raise APIException("new_start_time must be provided if new_end_time is provided.")
            event["end_time"] = new_end_time
        if new_description is not None:
            event["description"] = new_description
        if new_location is not None:
            event["location"] = new_location
        if new_attendees is not None:
            if username not in new_attendees:
                # add self, don't modify list externally
                new_attendees = new_attendees + [username]
            event["attendees"] = new_attendees
        return {"status": "success"}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """
        Check all required values
        """
        if prediction["response"] != ground_truth["response"] or prediction["exception"] != ground_truth["exception"]:
            return False

        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]

        for key, value in ground_truth_params.items():
            # all included values in ground truth are necessary
            if key not in predict_params:
                logger.debug(f"Key {key} not found in prediction parameters.")
                return False

            predict_value = predict_params[key]
            if predict_value is None:
                logger.debug(f"Key {key} has None value in prediction parameters.")
                return False
            elif key in {"new_name", "new_description", "new_location"}:
                score = semantic_str_compare(value, predict_value)
                if score < 0.9:
                    logger.debug(f"Key {key} has low semantic similarity score of {score}.")
                    return False
            elif value != predict_value:
                logger.debug(f"Key {key} has different value {predict_value} != {value}.")
                return False

        return True


class QueryCalendar(API):
    description = "Query for events that occur in a time range."
    parameters = {
        'session_token': {
            'type': "string",
            'description': "User's session_token.",
            'required': True
        },
        'start_time': {
            'type': "string",
            'description': 'The start time of the meeting, in the pattern of %Y-%m-%d %H:%M:%S',
            "required": True
        },
        'end_time': {
            'type': "string",
            'description': 'The end time of the meeting, in the pattern of %Y-%m-%d %H:%M:%S',
            "required": True
        },
    }
    output = {
        'events': {
            "type": 'array',
            "item": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "item": {"type": "string"}},
                }
            },
            'description': 'list of events starting or ending in the time range'
        }
    }

    database_name = CALENDAR_DB_NAME
    is_action = False

    def call(self, session_token: str, start_time: str, end_time: str) -> dict:
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if username not in self.database:
            raise APIException(f"User {username} has no events.")

        start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        if start_time > end_time:
            raise APIException("Start time must be before end time.")

        events = []
        for event in self.database[username].values():
            # TODO would be faster if these were pre-sorted and pre-converted to datetime objects
            event_start = datetime.strptime(event["start_time"], '%Y-%m-%d %H:%M:%S')
            event_end = datetime.strptime(event["end_time"], '%Y-%m-%d %H:%M:%S')
            if start_time <= event_start <= end_time or start_time <= event_end <= end_time \
                    or (event_start <= start_time and event_end >= end_time):
                events.append(copy.deepcopy(event))
        return {"events": events}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        if prediction["exception"] != ground_truth["exception"]:
            return False
        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]
        if predict_params["session_token"] != ground_truth_params["session_token"]:
            return False
        predict_event_ids = set(event["event_id"] for event in prediction["response"]["events"])
        for event in ground_truth["response"]["events"]:
            if event["event_id"] not in predict_event_ids:
                return False
        return True


class CalendarSuite(APISuite):
    name = "Calendar"
    description = "This API lets a users manage events in their calendar."
    apis = [CreateEvent, DeleteEvent, ModifyEvent, QueryCalendar]
