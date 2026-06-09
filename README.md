# MEI LLM Code Generation Experiment

This repository contains the code, datasets, prompts, generated answers, tests, and analysis scripts used in an experiment on LLM-based support for software development, developed for the Experimental Methods in Computer Science course at the University of Coimbra.

The repository focuses on the **code generation** task. The written analysis, hypotheses, and statistical tests are kept in a separate report and are not part of this repository.

## Project goal

The goal of this project is to evaluate whether different LLMs can be relied on for programming tasks by comparing their generated code on a shared problem set. In this repository, multiple LLMs are run on the same set of problems, their outputs are stored, and the resulting code is analysed using correctness and code-quality metrics.

## Repository structure

```text
MEI/
├── output/
│   ├── answers/
│   ├── prompts/
│   ├── tests/
│   ├── chatgptv5.5_summary.csv
│   ├── claude_sonnet_4_6.csv
│   ├── claude_sonnet_4_6_details.csv
│   ├── claude_4_6_complexity.csv
│   ├── gemini_v3_flash.csv
│   ├── gemini_v3_flash_details.csv
│   ├── gemini_v3_flash_complexity.csv
│   ├── gpt5_5_complexity.csv
│   ├── llm_code_metrics.csv
│   ├── problem_set.csv
│   ├── problem_set.parquet
│   ├── result.csv
│   ├── run_all_for_one_llm.py
│   ├── run_all_for_one_llm1.py
│   ├── run_one_assert_by_assert.py
│   └── runner.py
├── problems_extraction.py
├── prompt_builder_script.py
├── prompt_sample.txt
├── requirements.txt
├── scripts/
│   └── merge_csvs.py
└── README_pipeline.md
```

## What each part does

### `output/answers/`
Stores the generated code answers produced by the evaluated LLMs.

### `output/prompts/`
Stores the prompts used to query each model.

### `output/tests/`
Stores the tests used to validate generated code.

### `output/*.csv`
Stores processed results and summaries. Based on the file names, the repository contains per-model result tables, detail tables, summary tables, and complexity outputs for GPT-5.5, Gemini v3 Flash, and Claude Sonnet 4.6.

Examples:
- `chatgptv5.5_summary.csv`: summary results for ChatGPT v5.5.
- `gemini_v3_flash.csv`: results for Gemini v3 Flash.
- `gemini_v3_flash_complexity.csv`: complexity-only output for Gemini v3 Flash.
- `claude_4_6_complexity.csv`: complexity output for Claude 4.6.
- `llm_code_metrics.csv`: combined metric table.
- `result.csv`: general merged execution result file.

### `output/*.py`
Stores automation scripts that implement different parts of the evaluation pipeline.

Key scripts include:
- `complexity.py`: computes code complexity metrics.
- `extract_metrics.py`: extracts evaluation metrics from generated solutions.
- `extract_tests_simple.py`: extracts or simplifies test-related data.
- `runner.py`: helper for executing a single answer against a single test.
- `run_all_for_one_llm.py`: runs the full process for a single model.
- `run_one_assert_by_assert.py`: runs tests in a more granular assert-by-assert way.

### `scripts/merge_csvs.py`
Merges the per-model stats CSVs and complexity CSVs into the final merged table.

## Final merged table

The final table produced by `scripts/merge_csvs.py` uses this schema:

| Column | Meaning |
|---|---|
| `problem_id` | Problem identifier |
| `llm` | Model name |
| `difficulty` | Difficulty inferred from `problem_id` |
| `passed` | Whether the solution passed the tests |
| `tests_passed` | Number of passed tests |
| `tests_total` | Total number of tests |
| `tests_passed_pct` | Percentage of passed tests |
| `loc` | Lines of code |
| `cyclomatic_complexity` | Cyclomatic complexity from the per-model complexity CSV |
| `error` | Derived from `passed` (`0` for true, `1` for false) |

## Merge behavior

`scripts/merge_csvs.py` merges the per-model stats CSVs in `output/` with their matching complexity CSVs and produces `output/merged_results.csv`.

- `llm` comes from the model name in the file name or folder name.
- `problem_id` is taken from the per-model stats CSV.
- `difficulty` is inferred from `problem_id` using these ranges: `0-10` Easy, `10-20` Medium, `20-30` Hard.
- `cyclomatic_complexity` is loaded from the corresponding `*_complexity.csv` file.
- `error` is derived from `passed`: `True -> 0`, `False -> 1`.
- The final CSV is ordered by numeric `problem_id` first, then `llm`.

## Root-level data and scripts

- `leetcode_train.parquet`: dataset source used to build or sample the problem collection.
- `problem_set.csv` and `problem_set.parquet`: the experiment problem set in tabular form.
- `problems_extraction.py`: extracts problems from the source dataset.
- `prompt_builder_script.py`: builds prompts for the selected tasks.
- `prompt_sample.txt`: prompt example or reference template.

## Main experimental variables

The main independent variable in this project is the **LLM being evaluated**. Problem identifier and difficulty level may also be used as grouping or control variables.

The main dependent variables are:

- **Code correctness**, usually represented as solved/not solved or as test pass information.
- **LOC**, as a simple code size metric.
- **Cyclomatic complexity**, as a structural complexity metric.

Cyclomatic complexity is a standard code metric that counts the number of independent paths through the program and is commonly computed in Python with tools such as Radon.

## Typical workflow

1. Extract or define the problem set.
2. Build the prompts.
3. Run one LLM or multiple LLMs on the same problems.
4. Save outputs under `output/answers/`.
5. Save prompts under `output/prompts/`.
6. Run correctness and metric extraction scripts.
7. Produce CSV summaries and per-model result files.
8. Merge the per-model CSVs into `output/merged_results.csv`.

## Quick runbook

1. Sample or prepare the problem set:

```bash
python problems_extraction.py --per-level 10 --seed 42 --output output/problem_set
```

2. Build per-problem prompts:

```bash
python prompt_builder_script.py --input output/problem_set.csv --output-dir output/prompts
```

3. Extract tests from the dataset:

```bash
python output/extract_tests_simple.py --input output/problem_set.csv --output-dir output/tests
```

4. Evaluate one model's answers:

```bash
python output/run_all_for_one_llm.py --answers-dir output/answers/<model_name> --tests-dir output/tests --model <model_name> --summary-output output/<model_name>_summary.csv --details-output output/<model_name>_details.csv
```

5. Merge the per-model CSVs into the final table:

```bash
python scripts/merge_csvs.py --input-dir output --output output/merged_results.csv
```

## Models & configuration

- Expected answers layout: `output/answers/<model_name>/<problem_id>.txt`.
- Model-generation is external to this repo. Place generated answers under the folder above before running evaluations.
- API keys or credentials should be set as environment variables, not committed to the repository.

## Data provenance & licensing

- `leetcode_train.parquet` is expected to be a local extract of a LeetCode-style dataset.
- Ensure you have rights to use and redistribute the dataset.
- The scripts require at least `problem_uid` and `test` columns in the dataset.

## Requirements

Install pinned dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Radon is recommended for cyclomatic complexity metrics.

## Expected outputs

Example final CSV schema:

`problem_id,llm,difficulty,passed,tests_passed,tests_total,tests_passed_pct,loc,cyclomatic_complexity,error`

Example row:

`1,chatgpt_v5.5,Easy,True,4,4,100.0,34,5,0`

