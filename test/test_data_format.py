"""
Unit tests for validating dataset format
"""
import os
import json

import pytest

from paper.apis import APIS_BY_NAME, ALL_APIS


@pytest.fixture
def data_path():
    this_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(this_dir, "..", "data"))


@pytest.fixture
def conversations(data_path):
    pass


@pytest.fixture
def databases(data_path):
    pass


@pytest.fixture
def api_to_database():
    pass


def test_session_tokens(conversations):
    """
    check that session tokens are set the same in metadata and user fields
    check that usernames are set the same in metadata and user fields
    ensure that simulated username is not an argument to any API
    ensure that location is the correct location supplied to APIs
    """
    pass


def test_database_ground_truths(conversations, databases, api_to_database):
    """check that all ground truth info are identical to the ones stored in databases"""
    pass


def test_database_keys(databases):
    """validate that database keys match information in values"""
    pass


def test_api_documentation():
    """validate that API documentation matches arguments"""
    pass
