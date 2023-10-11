import copy
from datetime import datetime
from typing import List, Optional

from .exceptions import APIException
from .api import API, APISuite
from .utils import semantic_str_compare, verify_email_format

EMAIL_DB_NAME = "Email"
"""
Email database schema:

username: str - key
emails: List[dict]
    email_id: str
    sender: str
    receivers: List[str]
    subject: str
    body: str
    date: str
"""


class SearchInbox(API):
    description = "Searches for emails matching filters returning 5 most recent results."
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
            'description': 'The email address of the sender.',
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
        "emails": {
            'type': 'array',
            "item": {
                "type": "object",
                "properties": {
                    "sender": {"type": "string", "description": "The sender of the email."},
                    "receivers": {
                        "type": "array", "item": {"type": "string"},
                        "description": "The receivers of the email."
                    },
                    "subject": {"type": "string", "description": "The subject of the email."},
                    "body": {"type": "string", "description": "The body of the email."},
                    "date": {"type": "string", "description": "The date of the email."},
                },
            },
            'description': 'List of emails matching search criteria.'
        },
    }
    is_action = False
    database_name = EMAIL_DB_NAME

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
            return {"emails": []}

        user_emails = list(self.database[username].values())
        if not user_emails:
            return {"emails": []}

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
        matched_emails = []
        for email in user_emails:
            email_date = datetime.strptime(email['date'], '%Y-%m-%d %H:%M:%S')
            if self.now_timestamp < email_date:
                # ignore "future" emails
                continue
            if sender is not None and sender != email['sender']:
                continue
            if start_date is not None and start_date > email_date:
                continue
            if end_date is not None and end_date < email_date:
                continue
            if keywords is not None:
                keyword_matches = [keyword in email["body"].lower() or keyword in email["subject"].lower() for keyword in keywords]
                matches_keyword = any(keyword_matches) if match_type == "any" else all(keyword_matches)
                if not matches_keyword:
                    continue
            matched_emails.append(email)

        matched_emails.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'), reverse=True)
        matched_emails = matched_emails[:5]
        matched_emails = copy.deepcopy(matched_emails)
        return {"emails": matched_emails}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """
        Query is correct as long as all ground truth emails are retrieved, no exception is thrown and session tokens are the same
        """
        if prediction["exception"] != ground_truth["exception"]:
            return False
        predict_token = prediction["request"]["parameters"]["session_token"]
        ground_truth_token = ground_truth["request"]["parameters"]["session_token"]
        if predict_token != ground_truth_token:
            return False

        # as long as ground_truth emails are contained in response emails, it's correct
        response_ids = {email["email_id"] for email in prediction['response']['emails']}
        ground_truth_emails = ground_truth['response']['emails']
        for email in ground_truth_emails:
            if email["email_id"] not in response_ids:
                return False
        return True


class SendEmail(API):
    description = 'Sends an email on behalf of a given user.'
    parameters = {
        "session_token": {
            'type': "string",
            'description': 'The session_token of the user.',
            'required': True
        },
        "to": {
            "type": "array",
            "items": {"type": "string"},
            'description': 'Receiving addresses of the email.',
            "required": True
        },
        "subject": {
            'type': "string",
            'description': 'The subject of the email.',
            "required": True
        },
        "body": {
            'type': "string",
            'description': 'The content of the email.',
            "required": True
        },
    }
    output = {
        "email_id": {
            'type': "string",
            'description': 'email_id on success'
        },
    }
    is_action = True

    def call(self, session_token: str, to: List[str], subject: str, body: str) -> dict:
        self.check_session_token(session_token)
        for email in to:
            if not verify_email_format(email):
                raise APIException(f'{email} is not a valid email address.')
        email_id = f"{self.random.randint(0, 0xff):02x}-{self.random.randint(0, 0xffff):04x}-{self.random.randint(0, 0xffffffff):08x}"
        return {"email_id": email_id}

    @staticmethod
    def check_api_call_correctness(prediction, ground_truth) -> bool:
        """Don't really care about response email id"""
        if prediction['exception'] != ground_truth['exception']:
            return False

        predict_params = prediction["request"]["parameters"]
        ground_truth_params = ground_truth["request"]["parameters"]

        # session_tokens must be the same
        if predict_params["session_token"] != ground_truth_params["session_token"]:
            return False

        # emails must be the same, though order unimportant
        if set(predict_params['to']) != set(ground_truth_params['to']):
            return False

        # subject and body must be relatively the same
        if semantic_str_compare(predict_params["subject"], ground_truth_params["subject"]) < 0.9:
            return False
        if semantic_str_compare(predict_params["body"], ground_truth_params["body"]) < 0.8:
            return False
        return True


class EmailSuite(APISuite):
    name = 'Email'
    description = 'This API lets a user send and search emails.'
    apis = [SendEmail, SearchInbox]
