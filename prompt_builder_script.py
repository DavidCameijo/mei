#!/usr/bin/env python3

import argparse
from pathlib import Path
import pandas as pd

PROMPT_TEMPLATE = """You are an expert Python programmer.

Your task is to solve the coding problem below using Python 3.
Follow the provided starter code exactly.
Return only the final code. Do not include explanations, comments, or markdown.

Problem description:
{problem_description}

Starter code:
{starter_code}

Requirements:
- Preserve the function/class signature.
- Use only standard Python libraries unless the starter code already imports something.
- Return only the final code.
"""

def safe_text(x):
    return "" if pd.isna(x) else str(x)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Paquerade CSV file")
    ap.add_argument("--output-dir", default="output/prompts", help="Folder for .txt files")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, row in df.iterrows():
        problem_id = row.get("problem_uid", idx + 1)
        prompt = PROMPT_TEMPLATE.format(
            problem_description=safe_text(row.get("problem_description", "")),
            starter_code=safe_text(row.get("starter_code", ""))
        )
        (out_dir / f"{problem_id}.txt").write_text(prompt, encoding="utf-8")

    print(f"Saved {len(df)} prompt files to {out_dir}")

if __name__ == "__main__":
    main()