"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
import copy
from datetime import datetime

from .api import API, APISuite
from .exceptions import APIException


ALARM_DB_NAME = "Alarm"


"""
Alarm database schema:

username: str - key
alarm_id: str
time: str
"""


class AddAlarm(API):
    description = "Adds an alarm for a set time."
    parameters = {
        'time': {
            'type': 'string',
            'description': 'The time for alarm. Format: %H:%M:%S',
            "required": True
        }
    }
    output = {
        'alarm_id': {'type': 'string', 'description': 'Alarm ID. Format: xxxx-xxxx.'}
    }

    database_name = ALARM_DB_NAME
    is_action = True
    requires_auth = True

    def call(self, session_token: str, time: str) -> dict:
        """
        Adds an alarm for a set time.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            time: The time for alarm. Format: %H:%M:%S
        """
        datetime.strptime(time, '%H:%M:%S')
        user_info = self.check_session_token(session_token)
        username = user_info['username']
        if username not in self.database:
            self.database[username] = dict()
        alarm_id = f"{self.random.randint(0, 0xffff):04x}-{self.random.randint(0, 0xffff):04x}"
        self.database[username][alarm_id] = {
            "alarm_id": alarm_id,
            "time": time,
        }
        return {"alarm_id": alarm_id}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        # check if request and exception are all the same
        if prediction["exception"] != ground_truth["exception"]:
            return False

        # we only care about values present in the ground truth
        # missing required parameters will result in exceptions
        for key, value in ground_truth["request"]["parameters"].items():
            if key not in prediction["request"]["parameters"]:
                return False
            predict_value = prediction["request"]["parameters"][key]
            if predict_value != value:
                return False
        return True


class DeleteAlarm(API):
    description = "Deletes an alarm given an alarm_id."
    parameters = {
        'alarm_id': {
            'type': 'string',
            'description': "Alarm ID. Format: xxxx-xxxx.",
            "required": True
        }
    }
    output = {
        'status': {'type': 'string', 'description': 'success or failed'}
    }

    database_name = ALARM_DB_NAME
    is_action = True
    requires_auth = True

    def call(self, session_token: str, alarm_id: str) -> dict:
        """
        Deletes an alarm given an alarm_id.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            alarm_id: Format: xxxx-xxxx.
        """
        user_info = self.check_session_token(session_token)
        username = user_info['username']
        if username not in self.database:
            raise APIException(f"Alarm {alarm_id} not found.")
        if alarm_id not in self.database[username]:
            raise APIException(f"Alarm {alarm_id} not found.")
        del self.database[username][alarm_id]
        return {"status": "success"}


class FindAlarms(API):
    description = "Finds alarms the user has set."
    parameters = {
        "start_range": {
            "type": "string",
            'description': "Optional starting time range to find alarms. Format: %H:%M:%S",
            "required": False
        },
        "end_range": {
            "type": "string",
            "description": "Optional ending time range to find alarms. Format: %H:%M:%S",
            "required": False
        }
    }
    output = {
        'alarms': {
            'type': 'array',
            "item": {
                "type": "object",
                "properties": {
                    "alarm_id": {"type": "string", "description": "Alarm ID. Format: xxxx-xxxx."},
                    "time": {"type": "string", "description": "The time of alarm clock. Format: %H:%M:%S."}
                }
            },
            'description': "list of alarms in the given time range."
        }
    }

    database_name = ALARM_DB_NAME
    is_action = False
    requires_auth = True

    def call(self, session_token: str, start_range: str = None, end_range: str = None) -> dict:
        """
        Finds alarms the user has set. Optionally takes in start and end time range to find alarms.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            start_range: Optional starting time range to find alarms. Format: %H:%M:%S
            end_range: Optional ending time range to find alarms. Format: %H:%M:%S
        """
        user_info = self.check_session_token(session_token)
        username = user_info['username']
        if username not in self.database:
            return {"alarms": []}
        if start_range is not None:
            start_range = datetime.strptime(start_range, '%H:%M:%S')
        if end_range is not None:
            end_range = datetime.strptime(end_range, '%H:%M:%S')
        if start_range is not None and end_range is not None and start_range > end_range:
            raise APIException('Start range must be earlier than end range.')

        alarms = []
        for alarm in self.database[username].values():
            alarm_time = datetime.strptime(alarm['time'], '%H:%M:%S')
            if start_range is not None and alarm_time < start_range:
                continue
            if end_range is not None and alarm_time > end_range:
                continue
            alarms.append(copy.deepcopy(alarm))
        return {"alarms": alarms}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """
        Correct if output alarm ids in ground truth are a subset or equal to alarm ids in response.
        """
        # default is if input, output and exception are all the same
        if prediction["exception"] != ground_truth["exception"]:
            return False
        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]
        if predict_params["session_token"] != ground_truth_params["session_token"]:
            return False
        response_ids = {alarm["alarm_id"] for alarm in prediction["response"]["alarms"]}
        for alarm in ground_truth["response"]["alarms"]:
            if alarm["alarm_id"] not in response_ids:
                return False
        return True


class AlarmSuite(APISuite):
    name = "Alarm"
    description = "This API contains tools for managing alarms."
    apis = [
        AddAlarm,
        DeleteAlarm,
        FindAlarms
    ]
