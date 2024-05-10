"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
import json
import logging
import os
from typing import List
from datetime import datetime
from collections import deque
from abc import ABC, abstractmethod

from tooltalk.apis import ALL_APIS
from tooltalk.apis.account import ACCOUNT_DB_NAME, DeleteAccount, UserLogin, LogoutUser, RegisterUser
from tooltalk.utils.file_utils import get_names_and_paths

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Handles execution of tools and maintains state of databases when simulating conversations.
    """
    def __init__(
            self,
            init_database_dir: str = None,
            ignore_list: List[str] = None,
            account_database: str = ACCOUNT_DB_NAME,
    ) -> None:
        self.databases = dict()
        self.database_files = dict()
        self.account_database = account_database
        self.ignore_list = ignore_list if ignore_list is not None else list()
        self.session_token = None

        for file_name, file_path in get_names_and_paths(init_database_dir):
            database_name, ext = os.path.splitext(file_name)
            if ext == ".json":
                self.database_files[database_name] = file_path
                with open(file_path, 'r', encoding='utf-8') as reader:
                    self.databases[database_name] = json.load(reader)
        if self.account_database not in self.databases:
            raise ValueError(f"Account database {self.account_database} not found")

        self.apis = {api.__name__: api for api in ALL_APIS if api.__name__ not in self.ignore_list}
        self.inited_tools = dict()
        self.now_timestamp = None

    def reset_executor(self):
        """
        Reset all tools and databases to their initial state.
        """
        self.databases = dict()
        for database_name, file_path in self.database_files.items():
            with open(file_path, 'r', encoding='utf-8') as reader:
                self.databases[database_name] = json.load(reader)
        self.inited_tools = dict()
        self.now_timestamp = None
        self.session_token = None

    def get_init_tool(self, tool_name: str):
        if tool_name in self.inited_tools:
            return self.inited_tools[tool_name]
        cls = self.apis[tool_name]
        account_db = self.databases.get(self.account_database)
        if cls.database_name is not None:
            database = self.databases.get(cls.database_name)
            tool = cls(
                account_database=account_db,
                now_timestamp=self.now_timestamp,
                api_database=database,
            )
        else:
            tool = cls(
                account_database=account_db,
                now_timestamp=self.now_timestamp,
            )

        self.inited_tools[tool_name] = tool
        return tool

    def execute_tool(self, api_name: str, parameters: dict):
        request = {
            "api_name": api_name,
            "parameters": parameters
        }
        if api_name not in self.apis:
            response = {
                "response": None,
                "exception": f"API {api_name} not found"
            }
            return request, response

        tool = self.get_init_tool(api_name)
        if tool.requires_auth:
            if self.session_token is None:
                response = {
                    "response": None,
                    "exception": "User is not logged in"
                }
                return request, response
            parameters["session_token"] = self.session_token
        if api_name in [UserLogin.__name__, RegisterUser.__name__] and self.session_token is not None:
            username = tool.check_session_token(self.session_token)["username"]
            response = {
                "response": None,
                "exception": f"Only one user can be logged in at a time. Current user is {username}.",
            }
            return request, response

        # execute tool
        response = tool(**parameters)

        # capture session_token and simulate login and logout
        if api_name in [UserLogin.__name__, RegisterUser.__name__] and response["exception"] is None:
            self.session_token = response["response"]["session_token"]
        elif api_name in [LogoutUser.__name__, DeleteAccount.__name__] and response["exception"] is None:
            self.session_token = None
        return request, response

    def compare_api_calls(self, prediction: dict, ground_truth: dict) -> bool:
        api_name = prediction["request"]["api_name"]
        if api_name != ground_truth["request"]["api_name"]:
            return False

        # TODO add session_token if ground truth needs it
        return self.apis[api_name].check_api_call_correctness(prediction, ground_truth)

    def is_action(self, api_name: str) -> bool:
        if api_name not in self.apis:
            return False
        return self.apis[api_name].is_action

    def evaluate_predictions(self, conversation_with_predictions: dict) -> dict:
        """
        Compare predictions in a conversation with complete ground truth in conversation returning metrics.
        Calculates recall over ground truth, where predictions can only match to function in ground truth once.
        Additionally, calculates action precision, number of actions that match ground truth.
        Finally, calculates success, which is recall == 1.0 and action precision == 1.0.

        Metrics:
            predictions: number of predictions
            ground_truths: number of ground truths
            matches: number of predictions that match ground truth
            actions: number of predictions that are actions
            valid_actions: number of actions that match ground truth
            bad_actions: number of actions that don't match ground truth
            precision: matches / predictions
            recall: matches / ground_truths
            action_precision: valid_actions / actions
            bad_action_rate: bad_actions / actions
            success: recall == 1.0 and bad_action_rate == 0.0
        """
        predictions = list()
        ground_truths = list()
        for turn in conversation_with_predictions["conversation"]:
            if turn["role"] == "User":
                continue
            if "predictions" in turn:
                # last prediction will be assistant response
                for prediction in turn["predictions"]:
                    if prediction['role'] == 'api':
                        predictions.append(prediction)
            if "apis" in turn:
                ground_truths.extend(turn["apis"])

        # remove ground truth as they get matched to predictions
        match_count = 0
        action_count = 0
        valid_action_count = 0
        bad_action_count = 0
        current_ground_truths = deque(ground_truths)
        for prediction in predictions:
            is_match = False
            new_ground_truths = deque()
            while current_ground_truths:
                ground_truth = current_ground_truths.popleft()
                if self.compare_api_calls(prediction, ground_truth):
                    # don't add back in ground truth that matches
                    is_match = True
                    ground_truth["match"] = True
                    break
                else:
                    new_ground_truths.append(ground_truth)
            else:
                logger.debug(f"Failed {json.dumps(prediction, indent=4)}")

            # alter prediction data
            is_action = self.is_action(prediction["request"]["api_name"])
            is_successful = prediction["exception"] is None
            is_bad_action = not is_match and is_action and is_successful
            prediction["match"] = is_match
            prediction["bad_action"] = is_bad_action

            # add back in ground truths that don't match
            while current_ground_truths:
                new_ground_truths.append(current_ground_truths.popleft())
            current_ground_truths = new_ground_truths

            # update counters
            match_count += is_match
            action_count += is_action
            valid_action_count += is_action and is_match
            bad_action_count += is_bad_action

        for ground_truth in current_ground_truths:
            ground_truth["match"] = False

        precision = match_count / len(predictions) if len(predictions) > 0 else 0
        recall = match_count / len(ground_truths)
        action_precision = valid_action_count / action_count if action_count > 0 else 1
        bad_action_rate = bad_action_count / action_count if action_count > 0 else 0
        success = recall == 1.0 and bad_action_rate == 0.0
        soft_success = recall * (1.0 - bad_action_rate)
        metrics = {
            "predictions": len(predictions),
            "ground_truths": len(ground_truths),
            "matches": match_count,
            "actions": action_count,
            "valid_actions": valid_action_count,
            "bad_actions": bad_action_count,
            "precision": precision,
            "recall": recall,
            "action_precision": action_precision,
            # number of actions matching ground truth
            "bad_action_rate": bad_action_rate,
            # how often an action is bad aka successful but not matching ground truth
            "success": success,
            "soft_success": soft_success,
        }
        conversation_with_predictions["metrics"] = metrics
        return conversation_with_predictions

    def init_conversation_state(self, metadata: dict, api_history: list, user_data: dict = None) -> None:
        self.reset_executor()
        self.now_timestamp = datetime.strptime(metadata["timestamp"], "%Y-%m-%d %H:%M:%S")

        # setting these should never fail, if it does it's a bug in the dataset
        if "session_token" in user_data:
            username = user_data["username"]
            self.session_token = user_data["session_token"]
            self.databases[self.account_database][username]["session_token"] = user_data["session_token"]
        if "verification_code" in user_data:
            username = user_data["username"]
            self.databases[self.account_database][username]["verification_code"] = user_data["verification_code"]

        for api in api_history:
            # this should also never fail, if it does it's a bug in dataset
            self.execute_tool(**api["request"])

    def run_conversation(self, conversation: dict, predict_func: callable):
        """
        Simulates a conversation, calling prediction function
        """
        metadata = conversation["metadata"]
        user_data = conversation.get("user")
        ground_truth_history = list()
        api_history = list()

        for turn in conversation["conversation"]:
            if turn["role"] == "user":
                ground_truth_history.append({
                    "role": "user",
                    "text": turn["text"]
                })
                continue

            if turn["role"] != "assistant":
                raise ValueError(f"turn role must be user or assistant, instead got {turn['role']}")

            # other turns should be the assistant and could contain API calls
            self.init_conversation_state(metadata, api_history, user_data)
            predictions = list()
            current_history = ground_truth_history.copy()
            while True:
                prediction = predict_func(metadata, current_history)
                if prediction["role"] == "assistant":
                    # done with predicting apis
                    predictions.append(prediction)
                    break
                elif prediction["role"] == "api":
                    # execute api call
                    if prediction["request"]["parameters"] is None:
                        request = prediction["request"]
                        response = {
                            "response": None,
                            "exception": "Failed to parse API call"
                        }
                    else:
                        request, response = self.execute_tool(**prediction["request"])
                    prediction_and_response = {
                        "request": request,
                        "response": response["response"],
                        "exception": response["exception"],
                        "metadata": prediction.get("metadata")
                    }
                    predictions.append(prediction_and_response)
                    prediction_and_response["role"] = "api"
                    current_history.append(prediction_and_response)
                else:
                    raise ValueError(f"prediction role should be api or assistant, instead got {prediction['role']}")

            # add predictions to original conversation object
            turn["predictions"] = predictions
            if "apis" in turn:
                for api in turn["apis"]:
                    api_history.append(api)
                    ground_truth_history.append({
                        "role": "api",
                        "request": api["request"],
                        "response": api["response"],
                        "exception": api["exception"]
                    })
            ground_truth_history.append({
                "role": "assistant",
                "text": turn["text"]
            })

        return conversation


class BaseAPIPredictor(ABC):
    @abstractmethod
    def __init__(self, function_docs: List[dict], *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def predict(self, metadata: dict, conversation_history: dict) -> dict:
        raise NotImplementedError

    def __call__(self, metadata: dict, conversation_history: dict) -> dict:
        """Simple wrapper for convenience."""
        return self.predict(metadata, conversation_history)
