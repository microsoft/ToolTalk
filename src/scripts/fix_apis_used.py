import argparse
import json
import os
from functools import lru_cache

from tooltalk.apis import SUITES_BY_NAME


@lru_cache(maxsize=None)
def api_name_to_suite_name(api_name: str) -> str:
    for suite_name, suite in SUITES_BY_NAME.items():
        for api in suite.apis:
            if api.__name__ == api_name:
                return suite_name
    raise ValueError(f"API {api_name} not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", dest="dataset_dir", required=True, type=str,
                        help="Dataset directory")
    args = parser.parse_args()
    
    for fn in os.listdir(args.dataset_dir):
        path = os.path.join(args.dataset_dir, fn)
        with open(path, "r", encoding='utf-8') as reader:
            conversation = json.load(reader)

        apis_used = []
        for turn in conversation["conversation"]:
            if "apis" in turn:
                for api in turn["apis"]:
                    apis_used.append(api["request"]["api_name"])
        apis_used = list(set(apis_used))
        if set(conversation["apis_used"]) != set(apis_used):
            print(f"Fixing {fn}:", conversation["apis_used"], "=>", apis_used)
            conversation["intended_apis_used"] = conversation["apis_used"]
            conversation["apis_used"] = apis_used
            
            conversation["intended_suites_used"] = conversation["suites_used"]
            conversation["suites_used"] = list(set(
                api_name_to_suite_name(api_name) for api_name in apis_used
            ))

            with open(path, "w", encoding='utf-8') as writer:
                json.dump(conversation, writer, indent=4)
        else:
            print(f"No need to fix {fn}, skipping ...")


if __name__ == '__main__':
    main()
