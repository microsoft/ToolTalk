import os
from typing import List, Optional
from random import Random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from .exceptions import APIException


class API(ABC):
    description: str
    parameters: dict
    output: dict
    is_action: bool
    database_name: Optional[str] = None

    def __init__(
            self,
            account_database: dict,
            now_timestamp: str,
            api_database: dict = None
    ) -> None:
        self.account_database = account_database
        if api_database is not None:
            self.database = api_database
        else:
            self.database = dict()

        self.random = Random(489)  # TODO is seeded random enough for simulation and reproducibility?

        if isinstance(now_timestamp, str):
            self.now_timestamp = datetime.strptime(now_timestamp, "%Y-%m-%d %H:%M:%S")
        elif isinstance(now_timestamp, datetime):
            self.now_timestamp = now_timestamp
        else:
            raise ValueError(f"Invalid now_timestamp: {now_timestamp}")

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
        # default is if request, response, and exception are all the same
        if prediction["response"] != ground_truth["response"] \
                or prediction["exception"] != ground_truth["exception"]:
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

    @abstractmethod
    def call(self, **kwargs) -> dict:
        raise NotImplementedError

    def __call__(self, **kwargs) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - kwargs (dict): the parameters to call the API with.

        Returns:
        - response (dict): the response from the API call.
        """
        try:
            return {
                "response": self.call(**kwargs),
                "exception": None
            }
        except APIException as e:
            # Catch only expected Exceptions in debug mode
            return {
                "response": None,
                "exception": str(e)
            }
        except Exception as e:
            if os.environ.get("API_TALK_DEBUG", False):
                raise
            return {
                "response": None,
                "exception": str(e)
            }

    @classmethod
    def to_docstring(cls) -> str:
        lines = [
            f"{cls.__name__}: {cls.description}",
            "Parameters:"
        ]
        for name, attributes in cls.parameters.items():
            lines.append(f"- {name} ({attributes['type']}) {attributes['description']}")
        lines.append(f"Returns:")
        for name, attributes in cls.output.items():
            lines.append(f"- {name} ({attributes['type']}) {attributes['description']}")
        return "\n".join(lines)

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "name": cls.__name__,
            "description": cls.description,
            "parameters": cls.parameters,
            "output": cls.output
        }

    @classmethod
    def to_openai_doc(cls, disable_doc: bool = False) -> dict:
        parameters = dict()
        required = list()
        for name, attributes in cls.parameters.items():
            if attributes["required"]:
                required.append(name)
            attributes = attributes.copy()
            del attributes["required"]
            if disable_doc:
                attributes["description"] = ""
            parameters[name] = attributes
        description = "" if disable_doc else cls.description
        return {
            "name": cls.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
            },
            "required": required,
        }

    def check_session_token(self, session_token: str) -> dict:
        """
        Retrieves a user from the database by session_token.
        """
        for username, user_data in self.account_database.items():
            if session_token == user_data['session_token']:
                return user_data
        raise APIException('Invalid session_token.')


@dataclass
class APISuite:
    name: str
    description: str
    apis: List[API]

    @classmethod
    def to_docstring(cls) -> str:
        lines = [
            cls.name,
            cls.description,
            "APIs:"
        ]
        for api in cls.apis:
            lines.append(api.to_docstring())
        return "\n".join(lines)

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "name": cls.name,
            "description": cls.description,
            "apis": [api.to_dict() for api in cls.apis]
        }

    @classmethod
    def to_openai_doc(cls) -> dict:
        return [api.to_openai_doc() for api in cls.apis]
