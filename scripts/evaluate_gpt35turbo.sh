#!/usr/bin/env bash

output_dir="output/gpt-3.5"

python -m tooltalk.evaluate.evaluate_openai --dataset data/easy --model gpt-3.5-turbo --output_dir $output_dir/easy
python -m tooltalk.evaluate.evaluate_openai --dataset data/tooltalk --model gpt-3.5-turbo --output_dir $output_dir/hard
python -m tooltalk.evaluate.calculate_error_types --dataset $output_dir/easy --metrics $output_dir/easy_metrics.json
python -m tooltalk.evaluate.calculate_error_types --dataset $output_dir/hard --metrics $output_dir/hard_metrics.json
