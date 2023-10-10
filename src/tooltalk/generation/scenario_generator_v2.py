"""
This script randomly samples API suites from API Bank and prompts GPT4 to generate queries that make use of at least
one API from each sampled suite.
"""
import logging
import os
import re
import json
import argparse
from itertools import combinations
from typing import Optional, List

from tqdm import tqdm

from tooltalk.utils.openai_utils import openai_completion
from tooltalk.apis import ALL_SUITES
from tooltalk.file_utils import chunkify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_DOC_KEY = "{{API_DOCS}}"
REQUIRED_API_KEY = "{{REQUIRED_API}}"


def extract_scenarios(responses):
    extracted_scenarios = list()
    scenario_regex = re.compile(r"\s*- Scenario \d: (?P<scenario>.*)\s*")
    for response in responses:
        full_response = response
        raw_scenarios = scenario_regex.split(full_response)
        # TODO extract APIs used and scenarios from format
        scenarios = list()
        for scenario in raw_scenarios:
            scenario = scenario.strip()
            if scenario == "":
                continue
            scenarios.append(scenario)
        extracted_scenarios.append(scenarios)
    return extracted_scenarios


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=str, help="Path to prompt file")
    parser.add_argument("--model", type=str, default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--api_counts", type=int, nargs="+", default=[3], help="Number of suites to use")
    parser.add_argument("--api_key", type=str, help="Optional API key for endpoint")
    parser.add_argument("--max_tokens", type=int, nargs="+", default=[25000], help="Maximum number of tokens to generate")
    parser.add_argument("--temperature", type=float, default=0, help="Temperature for sampling")
    parser.add_argument("--beams", type=int, default=1, help="Number of beams to use for generation")
    parser.add_argument("--batch_size", type=int, default=10, help="Batch size for generation")
    parser.add_argument("--output_dir", type=str, help="Path to output directory")
    parser.add_argument("--reset", action="store_true", help="Reset output directory if it exists")

    return parser


# TODO use every API, then sample remainder in actual dataset generation run
# TODO special consideration for Account API?
def main(flags: Optional[List[str]] = None) -> None:
    parser = get_arg_parser()
    args = parser.parse_args(flags)

    # load template
    with open(args.prompt, 'r', encoding='utf-8') as reader:
        prompt_template = reader.read()

    if API_DOC_KEY not in prompt_template:
        raise ValueError(f"Prompt template must contain key {API_DOC_KEY}")

    os.makedirs(args.output_dir, exist_ok=True)
    # TODO make async
    for k in tqdm(args.api_counts):
        if k > len(ALL_SUITES):
            logger.warning(f"Skipping {k} API suites because there are only {len(ALL_SUITES)}")
            continue
        output_dicts = list()
        for combination in combinations(ALL_SUITES, k):
            formatted_apis = [
                api.to_docstring()
                for suite in combination
                for api in suite.apis
            ]
            api_doc_prompt = prompt_template.replace(API_DOC_KEY, '\n\n'.join(formatted_apis))
            for suite in combination:
                for api in suite.apis:
                    prompt = api_doc_prompt.replace(REQUIRED_API_KEY, api.__name__)
                    output_dicts.append({
                        "prompt": prompt,
                        "apis": {
                            "suites": [suite.name for suite in combination],
                            "required_api": api.__name__
                        }
                    })

        for batch in tqdm(chunkify(output_dicts, args.batch_size)):
            prompts = [output_dict["prompt"] for output_dict in batch]
            for max_tokens in args.max_tokens:
                try:
                    response_texts = openai_completion(
                        model=args.model,
                        prompts=prompts,
                        max_tokens=max_tokens,
                        temperature=args.temperature,
                        stop="```"
                    )
                except ValueError as error:
                    logger.error(f"Failed output using {max_tokens}: {error}")
                    logger.info(response_texts)
                    continue
                else:
                    scenarios = extract_scenarios(response_texts)
                    logger.info(f"Number of scenarios generated {list(map(len, scenarios))}")
                    for output_dict, response, scenario in zip(batch, response_texts, scenarios):
                        output_dict["response"] = response
                        output_dict["scenarios"] = scenario
                    break
            else:
                logger.warning("Reached max token limit skipping example")

            for output_dict in batch:
                if "response" not in output_dict:
                    continue
                # Write to file
                output_name = "-".join(output_dict["apis"]["suites"]) + "-" + output_dict["apis"]["required_api"] + ".json"
                output_path = os.path.join(args.output_dir, output_name)
                with open(output_path, 'w', encoding='utf-8') as writer:
                    json.dump(output_dict, writer, indent=4)


if __name__ == '__main__':
    main()
