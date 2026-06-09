# Updated LeetCode LLM Evaluation Pipeline

This version evaluates pasted LLM answers using the dataset test field.

## What it now does
- Samples 10 Easy + 10 Medium + 10 Hard problems.
- Saves `test` and `entry_point` from the dataset.
- Lets you paste raw LLM answers into text files.
- Extracts Python code automatically.
- Checks Python syntax.
- Runs the dataset-provided `check(candidate)` test.
- Produces per-tool CSVs and a summary CSV.

## Commands

### 1. Create problem set
```bash
python leetcode_llm_pipeline.py init --split train --seed 42 --per-level 10
```

### 2. Paste answers
Put the raw answer for each problem UID into:
- `output/answers/chatgpt/1.txt`
- `output/answers/claude/1.txt`
- `output/answers/gemini/1.txt`

### 3. Evaluate
```bash
python leetcode_llm_pipeline.py eval --tool chatgpt
python leetcode_llm_pipeline.py eval --tool claude
python leetcode_llm_pipeline.py eval --tool gemini
```

### 4. Summary
```bash
python leetcode_llm_pipeline.py summary
```

## Main output columns
- `syntax_parse_ok`
- `dataset_test_passed`
- `dataset_test_result`

## Important note
Some dataset tests may require helper classes/functions already expected by the problem. If a test fails because of missing environment definitions, that will appear in `dataset_test_result`, and you may need to adapt those specific problems manually.
