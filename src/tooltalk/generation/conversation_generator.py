"""
This script randomly samples API suites from API Bank and prompts GPT4 to generate queries that make use of at least
one API from each sampled suite.
"""
import os
import re
import json
import logging
import argparse
from typing import Optional, List

from tqdm import tqdm

from paper.llm_api_handler import CompletionsAPIHandler
from paper.apis import ALL_SUITES
from plugineval.auth import URIConstants
from plugineval.utils import chunkify, get_names_and_paths

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


QUERY_KEY = "{{QUERY}}"
API_DOC_KEY = "{{API_DOCS}}"


def extract_conversations(responses):
    turn_regex = re.compile(r"- User: (?P<user>.*)\n- APIs used: (?P<apis>.*)\n- Assistant: (?P<assistant>.*)")
    extracted_conversations = list()
    for response in responses:
        raw_conversations = "- User: " + response
        raw_turns = raw_conversations.split('\n\n')
        conversation = list()
        for turn in raw_turns:
            match = turn_regex.match(turn)
            assert match is not None, f"Turn did not match regex: \"{turn}\""
            user_text = match.group("user")
            apis = [api.strip() for api in match.group("apis").split(',')]
            assistant_text = match.group("assistant")
            conversation.append({
                "user": user_text,
                "apis": apis,
                "assistant": assistant_text
            })
        extracted_conversations.append(conversation)
    return extracted_conversations


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=str, help="Path to scenario files")
    parser.add_argument("--prompt", type=str, help="Path to prompt file")
    parser.add_argument("--openai_endpoint", type=str, default=URIConstants.SUBSTRATE_LLM_SDF, help="URL of OpenAI endpoint to use")
    parser.add_argument("--openai_key", type=str, help="API key for OpenAI endpoint")
    parser.add_argument("--max_tokens", type=int, nargs="+", default=[25600, 32000], help="Maximum number of tokens to generate")
    parser.add_argument("--temperature", type=float, default=0, help="Temperature for sampling")
    parser.add_argument("--batch_size", type=int, default=3, help="Batch size for generation")
    parser.add_argument("--output_dir", type=str, help="Path to output directory")

    return parser


# TODO use every API, then sample remainder in actual dataset generation run
# TODO special consideration for Account API?
def main(flags: Optional[List[str]] = None) -> None:
    parser = get_arg_parser()
    args = parser.parse_args(flags)

    # load template
    with open(args.prompt, 'r', encoding='utf-8') as reader:
        prompt_template = reader.read()

    llm_handler = CompletionsAPIHandler(
        endpoint=args.openai_endpoint,
        api_key_or_path=args.openai_key,
        retry_time=60,
        max_retries=5,
        request_timeout=180
    )

    os.makedirs(args.output_dir, exist_ok=True)
    for file_name, file_path in tqdm(get_names_and_paths(args.scenarios)):
        with open(file_path, 'r', encoding='utf-8') as reader:
            sample = json.load(reader)

        formatted_apis = [
            api.to_docstring()
            for suite in sample['apis']
            for api in ALL_SUITES[suite].apis
        ]

        prompts = list()
        for query in sample['queries']:
            prompt = prompt_template.replace(QUERY_KEY, query["scenario"])
            prompt = prompt.replace(API_DOC_KEY, '\n\n'.join(formatted_apis))
            prompts.append(prompt)

        # TODO make async
        all_responses = list()
        all_conversations = list()
        for batch in chunkify(prompts, args.batch_size):
            for max_tokens in args.max_tokens:
                try:
                    response_texts = llm_handler(
                        batch,
                        max_tokens=max_tokens,
                        temperature=args.temperature,
                    )
                    extracted_queries = extract_conversations(response_texts)
                except json.JSONDecodeError:
                    print(response_texts)
                    logger.info(f"JSON decode error with {max_tokens} tokens - retrying with larger max tokens")
                    continue
                else:
                    all_responses.extend(response_texts)
                    all_conversations.extend(extracted_queries)
                    break
            else:
                raise RuntimeError(f"Unable to generate responses using {max_tokens} tokens")

        assert len(prompts) == len(all_responses) == len(sample["queries"]) == len(all_conversations), "Number of prompts and responses must be equal"
        output_dict = list()
        for prompt, response, query, conversation in zip(prompts, all_responses, sample["queries"], all_conversations):
            output_dict.append({
                "prompt": prompt,
                "response": response,
                "queries": query,
                "apis": sample["apis"],
                "conversation": conversation,
            })

        # Write to file
        name = file_name.split(".")[0]
        output_path = os.path.join(args.output_dir, f"{name}_conversations.json")
        with open(output_path, 'w', encoding='utf-8') as writer:
            json.dump(output_dict, writer, indent=4)


if __name__ == '__main__':
    main()
