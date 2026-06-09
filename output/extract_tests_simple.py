#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='LeetCodeDataset CSV')
    ap.add_argument('--output-dir', default='output/tests', help='Folder for extracted tests')
    ap.add_argument('--id-col', default='problem_uid', help='Filename column')
    ap.add_argument('--test-col', default='test', help='Test code column')
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    if args.id_col not in df.columns:
        raise ValueError(f'Missing column: {args.id_col}')
    if args.test_col not in df.columns:
        raise ValueError(f'Missing column: {args.test_col}')

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for _, row in df.iterrows():
        pid = str(row[args.id_col]).strip()
        test_code = row[args.test_col]
        if pd.isna(test_code) or not str(test_code).strip():
            continue
        (out_dir / f'{pid}.txt').write_text(str(test_code).rstrip() + '\n', encoding='utf-8')
        count += 1

    print(f'Created {count} test files in {out_dir}')


if __name__ == '__main__':
    main()
