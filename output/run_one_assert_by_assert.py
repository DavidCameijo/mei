#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path

FENCE_RE = re.compile(r"```(?:python)?\s*|```", re.IGNORECASE)
ASSERT_RE = re.compile(r'^\s*assert\b.*$', re.MULTILINE)


def strip_fences(text):
    return FENCE_RE.sub('', text).strip()


def prepare_code(code):
    header = 'from typing import List\n'
    code = strip_fences(code)
    if 'from typing import List' not in code:
        code = header + code
    return code


def count_loc(code):
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith('#'))


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


def extract_asserts(test_code):
    return [m.group(0).strip() for m in ASSERT_RE.finditer(test_code)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--answer', required=True)
    ap.add_argument('--test', required=True)
    ap.add_argument('--model', default='unknown')
    ap.add_argument('--difficulty', default='')
    ap.add_argument('--summary-output', default='output/result_summary.csv')
    ap.add_argument('--details-output', default='output/result_details.csv')
    args = ap.parse_args()

    raw_code = Path(args.answer).read_text(encoding='utf-8', errors='ignore')
    code = prepare_code(raw_code)
    test_code = Path(args.test).read_text(encoding='utf-8', errors='ignore')
    asserts = extract_asserts(test_code)

    base_ns = {}
    summary = {
        'problem_id': Path(args.answer).stem,
        'model': args.model,
        'difficulty': args.difficulty,
        'answer_file': Path(args.answer).name,
        'test_file': Path(args.test).name,
        'passed': False,
        'tests_passed': 0,
        'tests_total': len(asserts),
        'tests_passed_pct': 0.0,
        'loc': count_loc(strip_fences(raw_code)),
        'error': ''
    }
    details = []

    try:
        exec(code, base_ns)
        candidate = get_candidate(base_ns)

        for i, assertion in enumerate(asserts, start=1):
            try:
                exec(assertion, {'candidate': candidate})
                details.append({
                    'problem_id': Path(args.answer).stem,
                    'test_id': i,
                    'assertion': assertion,
                    'passed': True,
                    'error': ''
                })
                summary['tests_passed'] += 1
            except Exception as e:
                details.append({
                    'problem_id': Path(args.answer).stem,
                    'test_id': i,
                    'assertion': assertion,
                    'passed': False,
                    'error': repr(e)
                })

        summary['passed'] = summary['tests_passed'] == summary['tests_total']
        summary['tests_passed_pct'] = (summary['tests_passed'] / summary['tests_total'] * 100.0) if summary['tests_total'] else 0.0

    except Exception as e:
        summary['error'] = repr(e)
        for i, assertion in enumerate(asserts, start=1):
            details.append({
                'problem_id': Path(args.answer).stem,
                'test_id': i,
                'assertion': assertion,
                'passed': False,
                'error': f'Runtime setup failure: {repr(e)}'
            })

    summary_out = Path(args.summary_output)
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    with summary_out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'problem_id', 'model', 'difficulty', 'answer_file', 'test_file',
            'passed', 'tests_passed', 'tests_total', 'tests_passed_pct', 'loc', 'error'
        ])
        writer.writeheader()
        writer.writerow(summary)

    details_out = Path(args.details_output)
    details_out.parent.mkdir(parents=True, exist_ok=True)
    with details_out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['problem_id', 'test_id', 'assertion', 'passed', 'error'])
        writer.writeheader()
        writer.writerows(details)

    print(f'Saved summary to {summary_out}')
    print(f'Saved details to {details_out}')


if __name__ == '__main__':
    main()
