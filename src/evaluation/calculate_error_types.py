import json
import logging
import argparse
from collections import Counter

from paper.utils.file_utils import get_names_and_paths

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str, help="Path to input file")
    parser.add_argument("--metrics", type=str, help="Path to metrics file")
    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    # over-trigger if bad action occurs in turn with no ground truth
    # bad planning occurs if function in ground truth does not appear in predictions for same turn
    # bad usage if function in ground truth appears in predictions for same turn but is incorrectly called
    over_trigger_count = 0
    bad_planning_count = 0
    bad_call_count = 0
    for _, path in get_names_and_paths(args.dataset):
        with open(path, "r", encoding='utf-8') as reader:
            conversation = json.load(reader)

        if conversation["metrics"]["success"]:
            continue

        for turn in conversation["conversation"]:
            if turn["role"] == "user":
                continue

            predictions = [prediction for prediction in turn["predictions"] if prediction["role"] == "api"]
            if "apis" not in turn:
                for prediction in predictions:
                    if prediction["bad_action"]:
                        over_trigger_count += 1
                continue

            bad_predictions = list()
            for prediction in predictions:
                if not prediction["match"]:
                    bad_predictions.append(prediction)

            unmatched_ground_truths = list()
            for ground_truth in turn["apis"]:
                if not ground_truth["match"]:
                    unmatched_ground_truths.append(ground_truth)

            if len(bad_predictions) == 0 and len(unmatched_ground_truths) == 0:
                # no problems with this turn
                continue

            ground_truth_names = Counter(
                ground_truth["request"]["api_name"] for ground_truth in unmatched_ground_truths)
            prediction_names = Counter(prediction["request"]["api_name"] for prediction in bad_predictions)
            if ground_truth_names.keys() == prediction_names.keys():
                for name, count in ground_truth_names.items():
                    if count < prediction_names[name]:
                        # didn't call tool enough times
                        bad_planning_count += 1
                        break
                else:
                    # called all necessary tools, but called incorrectly at least once
                    bad_call_count += 1
            else:
                # didn't call all necessary tools or irrelevant tools
                bad_planning_count += 1

    metrics = {
        "over-trigger": over_trigger_count,
        "bad planning": bad_planning_count,
        "bad call": bad_call_count,
    }
    logger.info(json.dumps(metrics))

    with open(args.metrics, "w", encoding='utf-8') as writer:
        json.dump(metrics, writer, indent=4)


if __name__ == '__main__':
    main()
