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

from paper.utils.openai_utils import openai_completion
from paper.apis import ALL_SUITES
from plugineval.utils import chunkify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_DOC_KEY = "{{API_DOCS}}"


def extract_scenarios(responses):
    extracted_scenarios = list()
    scenario_regex = re.compile(r"- Deliberate on APIs to use: (?P<apis>[a-zA-Z,\s]+)\n- Scenario: (?P<scenario>.*)")
    for response in responses:
        full_response = "- Deliberate on APIs to use:" + response
        raw_scenarios = full_response.split('\n\n')
        # TODO extract APIs used and scenarios from format
        scenarios = list()
        for scenario in raw_scenarios:
            match = scenario_regex.match(scenario)
            assert match is not None, f"Scenario did not match regex: \"{scenario}\""
            apis = [api.strip() for api in match.group("apis").split(',')]
            scenario = match.group("scenario")
            scenarios.append({
                "apis": apis,
                "scenario": scenario
            })
        extracted_scenarios.append(scenarios)
    return extracted_scenarios


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=str, help="Path to prompt file")
    parser.add_argument("--model", type=str, default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--api_counts", type=int, nargs="+", default=[3, 4, 5, 6, 7], help="Number of suites to use")
    parser.add_argument("--api_key", type=str, help="Optional API key for endpoint")
    parser.add_argument("--max_tokens", type=int, nargs="+", default=[25000], help="Maximum number of tokens to generate")
    parser.add_argument("--temperature", type=float, default=0, help="Temperature for sampling")
    parser.add_argument("--beams", type=int, default=1, help="Number of beams to use for generation")
    parser.add_argument("--batch_size", type=int, default=5, help="Batch size for generation")
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
    for k in tqdm(args.api_count):
        if k > len(ALL_SUITES):
            continue
        prompts = list()
        suites_used = list()
        for combination in combinations(ALL_SUITES, k):
            formatted_apis = [
                api.to_docstring()
                for suite in combination
                for api in suite.apis
            ]
            suites_used.append([suite.name for suite in combination])
            prompt = prompt_template.replace(API_DOC_KEY, '\n\n'.join(formatted_apis))
            prompts.append(prompt)

        all_responses = list()
        all_scenarios = list()
        for batch in chunkify(prompts, args.batch_size):
            for max_tokens in args.max_tokens:
                try:
                    response_texts = openai_completion(
                        model=args.model,
                        prompts=batch,
                        max_tokens=max_tokens,
                        temperature=args.temperature
                    )
                    extracted_scenario = extract_scenarios(response_texts)
                except AssertionError as error:
                    logger.error(f"Failed output using {max_tokens}: {error}")
                    logger.info(response_texts)
                    continue
                else:
                    logger.info(f"Number of scenarios generated {list(map(len, extracted_scenario))}")
                    all_responses.extend(response_texts)
                    all_scenarios.extend(extracted_scenario)
                    break
            else:
                raise ValueError("Reached max token limit")

        assert len(prompts) == len(all_responses) == len(suites_used) == len(all_scenarios), "Number of prompts and responses must be equal"
        for i, (prompt, response, apis, queries) in enumerate(zip(prompts, all_responses, suites_used, all_scenarios)):
            output_dict = {
                "prompt": prompt,
                "response": response,
                "scenarios": queries,
                "apis": apis,
            }

            # Write to file
            output_path = os.path.join(args.output_dir, f"{k}_apis_sample_{i}.json")
            with open(output_path, 'w', encoding='utf-8') as writer:
                json.dump(output_dict, writer, indent=4)


if __name__ == '__main__':
    main()
