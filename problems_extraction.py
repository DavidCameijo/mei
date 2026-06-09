#!/usr/bin/env python3
"""
sample_problems.py
==================
Randomly samples 10 Easy, 10 Medium, and 10 Hard problems
from the LeetCodeDataset (HuggingFace) and saves the full
rows to a CSV and Parquet file.

Usage:
    python sample_problems.py
    python sample_problems.py --per-level 10 --seed 42 --output problems
"""

import argparse
import pandas as pd
from pathlib import Path

file_name = "leetcode_train.parquet"


def load_dataset():
    print("Loading LeetCodeDataset...")
    df = pd.read_parquet(file_name)

    print(f"  Loaded {len(df)} problems.")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Difficulty counts:\n{df['difficulty'].value_counts().to_string()}")
    return df


def sample_problems(df, per_level=10, seed=42):
    parts = []
    for level in ["Easy", "Medium", "Hard"]:
        sub = df[df["difficulty"] == level]
        if len(sub) < per_level:
            raise ValueError(
                f"Not enough {level} problems: found {len(sub)}, need {per_level}."
            )
        sampled = sub.sample(per_level, random_state=seed)
        print(f"  Sampled {per_level} {level} problems.")
        parts.append(sampled)

    result = pd.concat(parts, ignore_index=True)
    result.insert(0, "problem_uid", range(1, len(result) + 1))
    return result


def save(df, output_stem):
    Path(output_stem).parent.mkdir(parents=True, exist_ok=True)
    csv_path  = f"{output_stem}.csv"
    parq_path = f"{output_stem}.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parq_path, index=False)
    print(f"\nSaved {len(df)} problems to:")
    print(f"  {csv_path}")
    print(f"  {parq_path}")


def main():
    ap = argparse.ArgumentParser(description="Sample LeetCode problems by difficulty.")
    ap.add_argument("--per-level", type=int, default=10)
    ap.add_argument("--seed",      type=int, default=42)
    ap.add_argument("--output",    type=str, default="output/problem_set")
    args = ap.parse_args()

    df      = load_dataset()
    sampled = sample_problems(df, per_level=args.per_level, seed=args.seed)

    print(f"\nSampled problem breakdown:")
    print(sampled[["problem_uid", "task_id", "difficulty"]].to_string(index=False))

    save(sampled, args.output)


if __name__ == "__main__":
    main()