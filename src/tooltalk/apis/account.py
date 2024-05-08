"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
from abc import ABC
from typing import Optional

from .exceptions import APIException
from .api import API, APISuite
from .utils import verify_phone_format, verify_email_format

"""
Account database schema:

username: str - key
password: str
session_token: str # use existence to determine if user is logged in
email: str
phone: str
name: str
"""

ACCOUNT_DB_NAME = "Account"


class AccountAPI(API, ABC):
    database_name = ACCOUNT_DB_NAME

    def __init__(
            self,
            account_database: dict,
            now_timestamp: str,
            api_database: dict = None
    ) -> None:
        super().__init__(account_database, now_timestamp, api_database)
        self.database = self.account_database


class ChangePassword(AccountAPI):
    description = 'Changes the password of an account.'
    parameters = {
        'old_password': {
            'type': "string",
            'description': 'The old password of the user.',
            'required': True,
        },
        'new_password': {
            'type': "string",
            'description': 'The new password of the user.',
            'required': True,
        },
    }
    output = {
        'status': {'type': "string", 'description': 'success or failed'}
    }
    database_name = ACCOUNT_DB_NAME
    is_action = True
    requires_auth = True

    def call(self, session_token: str, old_password: str, new_password: str) -> dict:
        """
        Changes the password of an account.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            old_password: The old password of the user.
            new_password: The new password of the user.
        """
        user_info = self.check_session_token(session_token)
        if user_info["password"] != old_password:
            raise APIException("The old password is incorrect.")
        user_info["password"] = new_password
        return {"status": "success"}


class DeleteAccount(AccountAPI):
    description = 'Deletes a user\'s account, requires user to be logged in.'
    parameters = {
        "password": {
            "type": "string",
            "description": "The password of the user.",
            "required": True
        }
    }
    output = {
        "status": {
            "type": "string",
            "description": "success or failed."
        }
    }
    is_action = True
    requires_auth = True

    def call(self, session_token: str, password: str) -> dict:
        """
        Deletes a user's account.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            password: The password of the user.
        """
        user_data = self.check_session_token(session_token)
        username = user_data['username']
        if user_data['password'] != password:
            raise APIException('The password is incorrect.')
        del self.database[username]
        return {"status": "success"}


class GetAccountInformation(AccountAPI):
    description = "Retrieves account information of logged in user."
    parameters = {}
    output = {
        "user": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "name": {"type": "string"},
            },
            "description": "The account information of the user."
        }
    }
    is_action = False
    requires_auth = True

    def call(self, session_token: str) -> dict:
        """
        Retrieves account information of logged in user.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
        """
        user_info = self.check_session_token(session_token)
        return {
            "user": {
                "username": user_info["username"],
                "email": user_info["email"],
                "phone": user_info["phone"],
                "name": user_info["name"],
            }
        }


class LogoutUser(AccountAPI):
    description = "Logs user out."
    parameters = {}
    output = {
        "status": {"type": "string", "description": "success or failed."},
    }
    is_action = True
    database_name = ACCOUNT_DB_NAME
    requires_auth = True

    def call(self, session_token: str) -> dict:
        """
        Logs user out.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
        """
        # check session_token will fail if user is already logged out
        user_data = self.check_session_token(session_token)
        user_data["session_token"] = None
        return {"status": "success"}


class QueryUser(AccountAPI):
    description = "Finds users given a username or email."
    parameters = {
        'username': {
            'type': "string",
            'description': 'The username of the user, required if email is not supplied.',
            "required": False
        },
        'email': {
            'type': "string",
            'description': 'The email of the user, required if username is not supplied. May match multiple users',
            "required": False
        },
    }
    output = {
        "users": {
            "type": "array",
            "item": {
                "type": "object",
                "description": "The account information of the user.",
                "properties": {
                    'username': {'type': "string", 'description': 'The username of the user.'},
                    'email': {'type': "string", 'description': 'The email of the user.'},
                    'phone': {'type': "string", 'description': 'The phone number of the user.'},
                    'name': {'type': "string", 'description': 'The name of the user.'},
                }
            },
            "description": "Users matching the query."
        }
    }
    database_name = ACCOUNT_DB_NAME
    is_action = False
    requires_auth = True

    def call(self, session_token: str, username: Optional[str] = None, email: Optional[str] = None) -> dict:
        """
        Finds users given a username or email.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            username: The username of the user, required if email is not supplied.
            email: The email of the user, required if username is not supplied. May match multiple users
        """
        self.check_session_token(session_token)
        if username is None and email is None:
            raise APIException("You need to provide at least one of username and email.")
        if username is None:
            return {
                "users": [
                    {
                        "username": username,
                        "email": user_data["email"],
                        "phone": user_data["phone"],
                        "name": user_data["name"],
                    }
                    for username, user_data in self.database.items()
                    if user_data["email"] == email
                ]
            }
        elif username in self.database:
            user_info = self.database[username]
            return {
                "users": [{
                    "username": username,
                    "email": user_info["email"],
                    "phone": user_info["phone"],
                    "name": user_info["name"],
                }]
            }
        else:
            return {"users": []}


class RegisterUser(AccountAPI):
    description = 'Register a new user.'
    parameters = {
        'username': {
            'type': "string",
            'description': 'The username of the user.',
            "required": True
        },
        'password': {
            'type': "string",
            'description': 'The password of the user.',
            "required": True
        },
        'email': {
            'type': "string",
            'description': 'The email of the user.',
            "required": True
        },
        "name": {
            "type": "string",
            "description": "The name of the user.",
            "required": False
        },
        "phone": {
            'type': "string",
            'description': 'The phone of the user in the format xxx-xxx-xxxx.',
            "required": False
        },
    }
    output = {
        "session_token": {'type': "string", 'description': 'The token of the user.'},
        'user': {'type': 'object', 'description': 'The account information of the user.'},
    }
    database_name = ACCOUNT_DB_NAME
    is_action = True

    def call(
            self,
            username: str,
            password: str,
            email: str,
            name: Optional[str] = None,
            phone: Optional[str] = None
    ) -> dict:
        """
        Register a new user.

        Args:
            username: The username of the user.
            password: The password of the user.
            email: The email of the user.
            name: The name of the user.
            phone: The phone of the user in the format xxx-xxx-xxxx.
        """
        if username in self.database:
            raise APIException('The username already exists.')
        if not verify_email_format(email):
            raise APIException("The email format is invalid.")
        if phone is not None and not verify_phone_format(phone):
            raise APIException("The phone number format is invalid.")
        session_token = f"{self.random.randint(0, 0xffffffff):08x}-{self.random.randint(0, 0xffff):04x}-{self.random.randint(0, 0xffff):04x}"  # TODO is this enough for a simulation?
        self.database[username] = {
            "username": username,
            'password': password,
            "session_token": session_token,
            'email': email,
            'phone': phone,
            "name": name,
        }
        return {
            "session_token": session_token,
            "user": {
                "username": username,
                "email": email,
                "phone": phone,
                "name": name,
            }
        }


class ResetPassword(AccountAPI):
    description = "Resets the password of a user using a verification code."
    parameters = {
        "username": {
            "type": "string",
            "description": "The username of the user.",
            "required": True
        },
        "verification_code": {
            "type": "string",
            "description": "The 6 digit verification code sent to the user.",
            "required": True
        },
        "new_password": {
            "type": "string",
            "description": "The new password of the user.",
            "required": True
        },
    }
    output = {
        "status": {
            "type": "string",
            "description": "success or failed"
        },
    }
    database_name = ACCOUNT_DB_NAME
    is_action = True

    def call(self, username: str, verification_code: str, new_password: str) -> dict:
        """
        Resets the password of a user using a verification code.

        Parameters:
        - username (str): the username of the user.
        - verification_code (str): the verification code sent to the user.
        - new_password (str): the new password of the user.

        Returns:
        - status (str): success or failed
        """
        if username not in self.database:
            raise APIException("The username does not exist.")
        if "verification_code" not in self.database[username]:
            raise APIException("The verification code is incorrect.")
        if self.database[username]["verification_code"] != verification_code:
            raise APIException("The verification code is incorrect.")
        self.database[username]["password"] = new_password
        return {"status": "success"}


class SendVerificationCode(AccountAPI):
    description = "Initiates a password reset for a user by sending a verification code to a backup email."
    parameters = {
        "username": {
            "type": "string",
            "description": "The username of the user.",
            "required": True
        },
        "email": {
            "type": "string",
            "description": "The email of the user.",
            "required": True
        },
    }
    output = {
        "status": {"type": "string", "description": "success or failed"},
    }
    database_name = ACCOUNT_DB_NAME
    is_action = True

    def call(self, username: str, email: str) -> dict:
        """
        Initiates a password reset for a user by sending a verification code to a backup email.

        Args:
            username: The username of the user.
            email: The email of the user.
        """
        if username not in self.database:
            raise APIException("The username does not exist.")
        if self.database[username]["email"] != email:
            raise APIException("The email is incorrect.")
        verification_code = f"{self.random.randint(0, 999999):06d}"
        self.database[username]["verification_code"] = verification_code
        return {"status": "success"}


class UpdateAccountInformation(AccountAPI):
    description = "Updates account information of a user."
    parameters = {
        "password": {
            "type": "string",
            "description": "The password of the user.",
            "required": True
        },
        "new_email": {
            "type": "string",
            "description": "The new email of the user.",
            "required": False
        },
        "new_phone_number": {
            "type": "string",
            "description": "The new phone number of the user in the format xxx-xxx-xxxx.",
            "required": False
        },
        "new_name": {
            "type": "string",
            "description": "The new name of the user.",
            "required": False
        }
    }
    output = {
        "success": {"type": "string", "description": "success or failed."},
    }
    is_action = True
    database_name = ACCOUNT_DB_NAME
    requires_auth = True

    def call(
            self,
            session_token: str,
            password: str,
            new_email: Optional[str] = None,
            new_phone_number: Optional[str] = None,
            new_name: Optional[str] = None
    ) -> dict:
        """
        Updates account information of a user.

        Args:
            session_token: User's session_token. Handled by ToolExecutor.
            password: The password of the user.
            new_email: The new email of the user.
            new_phone_number: The new phone number of the user in the format xxx-xxx-xxxx.
            new_name: The new name of the user.
        """
        user_data = self.check_session_token(session_token)
        username = user_data['username']
        if user_data['password'] != password:
            raise APIException('The password is incorrect.')
        if new_email is None and new_phone_number is None:
            raise APIException("You need to provide at least one of new_email and new_phone_number.")
        if new_email is not None:
            if not verify_email_format(new_email):
                raise APIException("The email is invalid.")
            self.database[username]["email"] = new_email
        if new_phone_number is not None:
            if not verify_phone_format(new_phone_number):
                raise APIException("The phone number is invalid.")
            self.database[username]["phone"] = new_phone_number
        if new_name is not None:
            self.database[username]["name"] = new_name
        return {"status": "success"}


class UserLogin(AccountAPI):
    description = 'Logs in a user returns a token.'
    parameters = {
        'username': {
            'type': "string",
            'description': 'The username of the user.',
            'required': True,
        },
        'password': {
            'type': "string",
            'description': 'The password of the user.',
            'required': True,
        },
    }
    output = {
        "session_token": {'type': "string", 'description': 'The token of the user.'},
    }
    database_name = ACCOUNT_DB_NAME
    is_action = True

    def call(self, username: str, password: str) -> dict:
        """
        Logs in a user returns a token.

        Args:
            username: The username of the user.
            password: The password of the user.
        """
        if username not in self.database:
            raise APIException('The username does not exist.')
        if self.database[username]['password'] != password:
            raise APIException('The password is incorrect.')
        if self.database[username]["session_token"] is not None:
            raise APIException('The user is already logged in.')

        session_token = f"{self.random.randint(0, 0xffffffff):08x}-{self.random.randint(0, 0xffff):04x}-{self.random.randint(0, 0xffff):04x}"
        self.database[username]["session_token"] = session_token
        return {"session_token": session_token}


class AccountSuite(APISuite):
    name = "AccountTools"
    description = "This API contains tools for account management."
    apis = [
        GetAccountInformation,
        DeleteAccount,
        UserLogin,
        LogoutUser,
        ChangePassword,
        RegisterUser,
        SendVerificationCode,
        ResetPassword,
        QueryUser,
        UpdateAccountInformation,
    ]
