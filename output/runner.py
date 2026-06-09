#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path

FENCE_RE = re.compile(r"```(?:python)?\s*|```", re.IGNORECASE)


def strip_fences(text):
    return FENCE_RE.sub('', text).strip()


def prepare_code(code):
    header = 'from typing import List\n'
    code = strip_fences(code)
    if 'from typing import List' not in code:
        code = header + code
    return code


def get_candidate(ns):
    if 'Solution' in ns:
        obj = ns['Solution']()
        methods = [m for m in dir(obj) if not m.startswith('_') and callable(getattr(obj, m))]
        if len(methods) == 1:
            return getattr(obj, methods[0])
        if methods:
            return getattr(obj, methods[0])
    funcs = [k for k, v in ns.items() if callable(v) and not k.startswith('_') and k != 'check']
    if len(funcs) == 1:
        return ns[funcs[0]]
    if funcs:
        return ns[funcs[0]]
    raise ValueError('No callable candidate found')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--answer', required=True)
    ap.add_argument('--test', required=True)
    ap.add_argument('--output', default='output/result.csv')
    args = ap.parse_args()

    code = prepare_code(Path(args.answer).read_text(encoding='utf-8', errors='ignore'))
    test_code = Path(args.test).read_text(encoding='utf-8', errors='ignore')

    ns = {}
    row = {
        'answer_file': Path(args.answer).name,
        'test_file': Path(args.test).name,
        'passed': False,
        'error': ''
    }

    try:
        exec(code, ns)
        candidate = get_candidate(ns)
        exec(test_code, ns)
        ns['check'](candidate)
        row['passed'] = True
    except Exception as e:
        row['error'] = repr(e)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['answer_file', 'test_file', 'passed', 'error'])
        writer.writeheader()
        writer.writerow(row)

    print(f'Saved 1 result to {out}')


if __name__ == '__main__':
    main()
