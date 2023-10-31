"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
import os
import json
import argparse

from paper.utils.file_utils import get_names_and_paths


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=str, help="Path to input file")

    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    for name, path in get_names_and_paths(args.input):
        with open(path, "r", encoding='utf-8') as reader:
            conversation = json.load(reader)

        if "session_token" in conversation["metadata"]:
            conversation["metadata"]["session_token"] = conversation["user"]["session_token"]
            conversation["metadata"]["username"] = conversation["user"]["username"]

        new_turns = list()
        for i, turn in enumerate(conversation["conversation"]):
            if "apis" in turn:
                indexed_apis = list()
                for api in turn["apis"]:
                    indexed_apis.append({"index": i, **api})
                turn["apis"] = indexed_apis
            new_turns.append({"index": i, **turn})
        conversation["conversation"] = new_turns

        with open(path, "w", encoding='utf-8') as writer:
            json.dump(conversation, writer, indent=4)


if __name__ == '__main__':
    main()
