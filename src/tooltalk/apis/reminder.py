"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
import copy
from datetime import datetime
from typing import Optional

from .api import API, APISuite
from .exceptions import APIException
from .utils import semantic_str_compare

REMINDER_DB_NAME = "Reminder"
"""
username: str - key
reminders: dict of reminder ids
    reminder_id: str - key
    task: str
    due_date: str - optional
    status: str (pending, completed)
"""


class AddReminder(API):
    description = "Add a reminder."
    parameters = {
        "task": {
            "type": "string",
            "description": "The task to be reminded of.",
            "required": True
        },
        "due_date": {
            "type": "string",
            "description": "Optional date the task is due, in the format of %Y-%m-%d %H:%M:%S.",
            "required": False
        }
    }
    output = {"reminder_id": {"type": "string", "description": "reminder_id on success"}}
    is_action = True
    database_name = REMINDER_DB_NAME
    requires_auth = True

    def call(self, session_token: str, task: str, due_date: Optional[str] = None) -> dict:
        """
        Add a reminder.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            task: The task to be reminded of.
            due_date: Optional date the task is due, in the format of %Y-%m-%d %H:%M:%S.
        """
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if username not in self.database:
            self.database[username] = dict()
        if due_date is not None:
            try:
                datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise APIException(f"Invalid due_date: {due_date}")
        reminder_id = f"{self.random.randint(0, 0xff):02x}-{self.random.randint(0, 0xffff):04x}"
        self.database[username][reminder_id] = {
            "reminder_id": reminder_id,
            "task": task,
            "due_date": due_date,
            "status": "pending"
        }
        return {"reminder_id": reminder_id}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - ground_truth (dict): the ground truth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        # don't care about response
        if prediction["exception"] != ground_truth["exception"]:
            return False

        # we only care about values present in the ground truth
        # missing required parameters will result in exceptions
        for key, value in ground_truth["request"]["parameters"].items():
            if key not in prediction["request"]["parameters"]:
                return False
            predict_value = prediction["request"]["parameters"][key]
            if key == "due_date":
                # just check if date is valid, ignore time
                predict_date = datetime.strptime(predict_value, "%Y-%m-%d %H:%M:%S")
                true_date = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                if predict_date.date() != true_date.date():
                    return False
            elif key == "task":
                if semantic_str_compare(predict_value, value) < 0.9:
                    return False
            elif predict_value != value:
                return False
        return True


class CompleteReminder(API):
    description = "Complete a reminder."
    parameters = {
        "reminder_id": {
            "type": "string",
            "description": "The reminder_id of the reminder to be deleted.",
            "required": True
        }
    }
    output = {"status": {"type": "string", "description": "success or failure"}}
    is_action = True
    database_name = REMINDER_DB_NAME
    requires_auth = True

    def call(self, session_token: str, reminder_id: str) -> dict:
        """
        Complete a reminder.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            reminder_id: The reminder_id of the reminder to be deleted.
        """
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if reminder_id not in self.database[username]:
            raise APIException(f"Reminder {reminder_id} not found in database")
        if self.database[username][reminder_id]["status"] == "complete":
            raise APIException(f"Reminder {reminder_id} already completed")
        self.database[username][reminder_id]["status"] = "complete"
        return {"status": "success"}


class DeleteReminder(API):
    description = "Delete a reminder."
    parameters = {
        "reminder_id": {
            "type": "string",
            "description": "The reminder_id of the reminder to be deleted.",
            "required": True
        }
    }
    output = {"status": {"type": "string", "description": "success or failure"}}
    is_action = True
    database_name = REMINDER_DB_NAME
    requires_auth = True

    def call(self, session_token: str, reminder_id: str) -> dict:
        """
        Delete a reminder.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            reminder_id: The reminder_id of the reminder to be deleted.
        """
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if reminder_id not in self.database[username]:
            raise APIException(f"Reminder {reminder_id} not found in database")
        del self.database[username][reminder_id]
        return {"status": "success"}


class GetReminders(API):
    description = "Get a list of reminders."
    parameters = {}
    output = {
        "reminders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "string", "description": "reminder_id on success"},
                    "task": {"type": "string", "description": "The task to be reminded of."},
                    "due_date": {
                        "type": "string",
                        "description": "Optional date the task is due, in the format of %Y-%m-%d %H:%M:%S."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "completed"],
                        "description": "The status of the reminder, either 'pending' or 'completed'."
                    }
                }
            },
            "description": "List of reminders for user."
        },
    }
    is_action = False
    database_name = REMINDER_DB_NAME
    requires_auth = True

    def call(self, session_token: str) -> dict:
        """
        Get a list of reminders.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
        """
        user_info = self.check_session_token(session_token)
        username = user_info["username"]
        if username not in self.database:
            return {"reminders": []}
        reminders = list(self.database[username].values())
        reminders = copy.deepcopy(reminders)
        return {"reminders": reminders}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        # request and exception should be the same
        if prediction["request"] != ground_truth["request"] \
                or prediction["exception"] != ground_truth["exception"]:
            return False

        # api_ids in ground truth should be subset of api_ids in prediction
        prediction_reminders = prediction["response"]["reminders"]
        prediction_ids = {reminder["reminder_id"] for reminder in prediction_reminders}
        ground_truth_reminders = ground_truth["response"]["reminders"]
        for reminder in ground_truth_reminders:
            if reminder["reminder_id"] not in prediction_ids:
                return False
        return True


class ReminderSuite(APISuite):
    name = "Reminder"
    description = "A suite of APIs for managing reminders for a TODO list."
    apis = [
        AddReminder,
        GetReminders,
        DeleteReminder,
        CompleteReminder
    ]
