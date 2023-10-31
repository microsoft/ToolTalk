"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.

Ensure tool documentation is complete
"""
import inspect

from tooltalk.apis import ALL_APIS


def test_missing_documentation():
    for api in ALL_APIS:
        assert api.description is not None and api.description != "", f"API {api} is missing a description"
        api_sig = inspect.signature(api.call)
        for param_name, param in api.parameters.items():
            assert param["description"] is not None and param["description"] != "", \
                f"API {api} is missing a description for parameter {param_name}"
            assert param["type"] is not None and param["type"] != "", \
                f"API {api} is missing a type for parameter {param_name}"
            assert param["required"] is not None, \
                f"API {api} is missing a required flag for parameter {param_name}"

        doc_params = set(api.parameters.keys())
        sig_params = set(api_sig.parameters.keys())
        sig_params.remove("self")
        if "session_token" in sig_params:
            sig_params.remove("session_token")

        assert doc_params == sig_params, \
            f"API {api} has mismatched parameters between documentation and implementation"
