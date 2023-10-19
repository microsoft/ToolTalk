"""
Evaluate Tool LLM on API-Talk dataset.
"""
import os
import json
import logging
import argparse
from enum import Enum
from typing import List
from collections import Counter

import openai
from tqdm import tqdm

from tooltalk.apis import APIS_BY_NAME, ALL_APIS
from tooltalk.evaluation.tool_executor import ToolExecutor, BaseAPIPredictor
from tooltalk.utils.file_utils import get_names_and_paths
from tooltalk.utils.openai_utils import openai_chat_completion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAIPredictor(BaseAPIPredictor):
    system_prompt = "You are a helpful assistant. Here is some user data:" \
                    "\nlocation: {location}" \
                    "\ntimestamp: {timestamp}" \
                    "\nusername (if logged in): {username}"

    def __init__(self, model, apis_used, disable_docs=False):
        self.model = model
        self.api_docs = [api.to_openai_doc(disable_docs) for api in apis_used]

    def predict(self, metadata: dict, conversation_history: dict) -> dict:
        system_prompt = self.system_prompt.format(
            location=metadata["location"],
            timestamp=metadata["timestamp"],
            username=metadata.get("username")
        )

        openai_history = [{
            "role": "system",
            "content": system_prompt
        }]
        for turn in conversation_history:
            if turn["role"] == "user" or turn["role"] == "assistant":
                openai_history.append({
                    "role": turn["role"],
                    "content": turn["text"]
                })
            elif turn["role"] == "api":
                openai_history.append({
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": turn["request"]["api_name"],
                        "arguments": json.dumps(turn["request"]["parameters"])
                    }
                })
                response_content = {
                    "response": turn["response"],
                    "exception": turn["exception"]
                }
                openai_history.append({
                    "role": "function",
                    "name": turn["request"]["api_name"],
                    "content": json.dumps(response_content)
                })

        openai_response = openai_chat_completion(
            model=self.model,
            messages=openai_history,
            functions=self.api_docs,
        )
        logger.debug(f"OpenAI full response: {openai_response}")
        openai_message = openai_response["choices"][0]["message"]
        metadata = {
            "openai_request": {
                "model": self.model,
                "messages": openai_history,
                "functions": self.api_docs,
            },
            "openai_response": openai_response
        }
        if "function_call" in openai_message:
            function_call = openai_message["function_call"]
            api_name = function_call["name"]
            try:
                parameters = json.loads(function_call["arguments"])
            except json.decoder.JSONDecodeError:
                # check termination reason
                logger.info(f"Failed to decode arguments for {api_name}: {function_call['arguments']}")
                parameters = None
            return {
                "role": "api",
                "request": {
                    "api_name": api_name,
                    "parameters": parameters
                },
                # store metadata about call
                "metadata": metadata,
            }
        else:
            return {
                "role": "assistant",
                "text": openai_message["content"],
                # store metadata about call
                "metadata": metadata,
            }


class EvalModes(str, Enum):
    PREDICT = "predict"
    EVALUATE = "evaluate"
    VALIDATE = "validate"


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str, help="Path to dataset for models to evaluate")
    parser.add_argument("--database", type=str, help="Path to database used in evaluation")
    parser.add_argument("--api_key", type=str, default="openai.key", help="Path to OpenAI API key")
    parser.add_argument("--api_mode", type=str, choices=["exact", "suite", "all"], default="all",
                        help="API mode to use for evaluation, determines which api docs to include")
    parser.add_argument("--model", type=str, default="gpt-4", help="Model to use for generation")
    parser.add_argument("--output_dir", type=str, help="Path to output model predictions")
    parser.add_argument("--reset", action="store_true", help="reset evaluation writing over any cached results")
    parser.add_argument("--disable_documentation", action="store_true",
                        help="disabled documentation sent to GPT-4 replacing with empty strings")
    parser.add_argument("--modes", choices=list(EvalModes), type=str, nargs='+', default=list(EvalModes),
                        help="Evaluation modes")

    return parser


def main(flags: List[str] = None):
    parser = get_arg_parser()
    args = parser.parse_args(flags)

    # get api key
    openai_key = os.environ.get("OPENAI_KEY", None)
    if openai_key is None:
        with open(args.api_key, "r") as f:
            openai_key = f.read().strip()
    openai.api_key = openai_key

    total_metrics = Counter()
    os.makedirs(args.output_dir, exist_ok=True)
    tool_executor = ToolExecutor(init_database_dir=args.database)
    for file_name, file_path in tqdm(get_names_and_paths(args.dataset)):
        output_file_path = os.path.join(args.output_dir, file_name)
        if os.path.exists(output_file_path) and not args.reset:
            logger.info(f"Skipping {file_name} because it already exists")
            with open(output_file_path, 'r', encoding='utf-8') as reader:
                conversation_with_metrics = json.load(reader)
            total_metrics += conversation_with_metrics["metrics"]
            total_metrics["num_conversations"] += 1
            continue

        logger.info(f"Running {file_name}")
        with open(file_path, 'r', encoding='utf-8') as reader:
            conversation = json.load(reader)

        if EvalModes.PREDICT in args.modes:
            logger.info("Running prediction...")
            if args.api_mode == "exact":
                apis_used = [APIS_BY_NAME[api_name] for api_name in conversation["apis_used"]]
            elif args.api_mode == "suite":
                apis_used = [api for suite in conversation["suites_used"] for api in suite.apis]
            elif args.api_mode == "all":
                apis_used = ALL_APIS
            else:
                raise ValueError(f"Invalid api mode: {args.api_mode}")

            predictor_func = OpenAIPredictor(
                model=args.model,
                apis_used=apis_used,
                disable_docs=args.disable_documentation
            )
            conversation = tool_executor.run_conversation(conversation, predictor_func)

        if EvalModes.EVALUATE in args.modes:
            logger.info("Running evaluation...")
            conversation = tool_executor.evaluate_predictions(conversation)
            logger.info(f"Conversation {file_name} pass: {conversation['metrics']['success']}")
            total_metrics += conversation["metrics"]
            total_metrics["num_conversations"] += 1

            if EvalModes.VALIDATE in args.modes:
                logger.info("Validating evaluation...")
                for turn in conversation["conversation"]:
                    if "predictions" not in turn:
                        continue
                    for prediction in turn["predictions"]:
                        if prediction["role"] == "api":
                            assert "match" in prediction
                            assert "bad_action" in prediction

        with open(output_file_path, 'w', encoding='utf-8') as writer:
            json.dump(conversation, writer, indent=4)

    logger.info("Finished processing conversations")
    if EvalModes.EVALUATE in args.modes:
        metrics = {
            "num_conversations": total_metrics["num_conversations"],
            "precision": total_metrics["matches"] / total_metrics["predictions"],
            "recall": total_metrics["matches"] / total_metrics["ground_truths"],
            "action_precision": total_metrics["valid_actions"] / total_metrics["actions"],
            "bad_action_rate": total_metrics["bad_actions"] / total_metrics["actions"],
            "success_rate": total_metrics["success"] / total_metrics["num_conversations"]
        }
        logger.info(f"Metrics: {json.dumps(metrics, indent=4)}")


if __name__ == "__main__":
    main()
