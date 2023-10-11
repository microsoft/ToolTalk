#!/usr/bin/env bash

output_dir=$1

python -m tooltalk.evaluate.evaluate_openai
python -m tooltalk.evaluate.evaluate_openai
python -m tooltalk.evaluate.calculate_error_types
python -m tooltalk.evaluate.calculate_error_types
