#!/usr/bin/env python3
"""
MEI Assignment - LLM Code Generation Evaluation Pipeline
=========================================================
Usage:
    python pipeline.py init              # Sample 30 problems and create problem_set.csv
    python pipeline.py eval chatgpt      # Evaluate ChatGPT answers
    python pipeline.py eval claude       # Evaluate Claude answers
    python pipeline.py eval gemini       # Evaluate Gemini answers
    python pipeline.py summary           # Generate summary across all tools
"""

import os
import re
import ast
import sys
import json
import argparse
import pandas as pd
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
OUTPUT_DIR  = Path("output")
ANSWERS_DIR = OUTPUT_DIR / "answers"
RESULTS_DIR = OUTPUT_DIR / "results"
TOOLS       = ["chatgpt", "claude", "gemini"]


DATASET_FILE = "leetcode_train.parquet"

# ─── Step 1: Load and sample the dataset ──────────────────────────────────────
def load_dataset():
    df = pd.read_parquet(DATASET_FILE)
    print(f"  Loaded {len(df)} problems. Columns: {list(df.columns)}")
    return df


def sample_problems(df, per_level=10, seed=42):
    levels = ["Easy", "Medium", "Hard"]
    parts = []
    for level in levels:
        sub = df[df["difficulty"] == level]
        if len(sub) < per_level:
            raise ValueError(f"Not enough {level} problems ({len(sub)} found).")
        sampled = sub.sample(per_level, random_state=seed)
        parts.append(sampled)
        print(f"  Sampled {per_level} {level} problems.")
    result = pd.concat(parts, ignore_index=True)
    result.insert(0, "problem_uid", range(1, len(result) + 1))
    return result


def cmd_init(per_level=10, seed=42):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        (ANSWERS_DIR / tool).mkdir(parents=True, exist_ok=True)

    df      = load_dataset()
    sampled = sample_problems(df, per_level=per_level, seed=seed)

    out = RESULTS_DIR / "problem_set.csv"
    sampled.to_csv(out, index=False)
    print(f"\nProblem set saved to {out}")
    print(f"Total problems: {len(sampled)}")
    print(f"\nNext steps:")
    print(f"  1. Open output/results/problem_set.csv to see your 30 problems.")
    print(f"  2. For each problem, prompt each LLM tool in the web UI.")
    print(f"  3. Paste the raw answer into:")
    for tool in TOOLS:
        print(f"       output/answers/{tool}/<problem_uid>.txt")
    print(f"  4. Run: python pipeline.py eval <tool>")


# ─── Step 2: Code extraction ───────────────────────────────────────────────────
def extract_code(text):
    """Extract Python code from LLM answer (handles ```python blocks)."""
    matches = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S | re.I)
    if matches:
        return max(matches, key=len).strip()
    return text.strip()


# ─── Step 3: Test runner ───────────────────────────────────────────────────────
def run_tests(code_text, test_code, entry_point):
    """
    Execute candidate code against the dataset test function.
    The dataset provides a check(candidate) function as test code.
    """
    namespace = {}
    try:
        exec(code_text, namespace)

        candidate = eval(entry_point, namespace)

        test_namespace = namespace.copy()
        test_namespace["candidate"] = candidate
        exec(test_code, test_namespace)
        test_namespace["check"](candidate)

        return True, "Passed"
    except AssertionError as e:
        return False, f"AssertionError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ─── Step 4: Evaluate one tool ─────────────────────────────────────────────────
def cmd_eval(tool):
    problem_csv = RESULTS_DIR / "problem_set.csv"
    if not problem_csv.exists():
        print("ERROR: problem_set.csv not found. Run 'python pipeline.py init' first.")
        sys.exit(1)

    df       = pd.read_csv(problem_csv)
    tool_dir = ANSWERS_DIR / tool
    results  = []

    print(f"\nEvaluating {tool} ({len(df)} problems)...")

    for _, row in df.iterrows():
        uid      = int(row["problem_uid"])
        title    = row.get("task_id", uid)
        diff     = row.get("difficulty", "?")
        ans_file = tool_dir / f"{uid}.txt"

        result = {
            "problem_uid": uid,
            "task_id":     title,
            "difficulty":  diff,
            "tool":        tool,
            "answer_exists": ans_file.exists(),
            "code_extracted": False,
            "syntax_ok":    False,
            "tests_passed": False,
            "status":       "missing",
            "error":        ""
        }

        if not ans_file.exists():
            print(f"  [{uid:02d}] {title} ({diff}) → MISSING answer file")
            results.append(result)
            continue

        