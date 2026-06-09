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


def evaluate_one(answer_path, test_path, model, difficulty=''):
    raw_code = answer_path.read_text(encoding='utf-8', errors='ignore')
    code = prepare_code(raw_code)
    test_code = test_path.read_text(encoding='utf-8', errors='ignore')
    asserts = extract_asserts(test_code)

    summary = {
        'problem_id': answer_path.stem,
        'model': model,
        'difficulty': difficulty,
        'answer_file': answer_path.name,
        'test_file': test_path.name,
        'passed': False,
        'tests_passed': 0,
        'tests_total': len(asserts),
        'tests_passed_pct': 0.0,
        'loc': count_loc(strip_fences(raw_code)),
        'error': ''
    }
    details = []

    try:
        ns = {}
        exec(code, ns)
        candidate = get_candidate(ns)

        for i, assertion in enumerate(asserts, start=1):
            try:
                exec(assertion, {'candidate': candidate})
                details.append({
                    'problem_id': answer_path.stem,
                    'model': model,
                    'test_id': i,
                    'passed': True,
                    'error': ''
                })
                summary['tests_passed'] += 1
            except Exception as e:
                details.append({
                    'problem_id': answer_path.stem,
                    'model': model,
                    'test_id': i,
                    'passed': False,
                    'error': repr(e)
                })

        summary['passed'] = summary['tests_passed'] == summary['tests_total']
        summary['tests_passed_pct'] = (summary['tests_passed'] / summary['tests_total'] * 100.0) if summary['tests_total'] else 0.0

    except Exception as e:
        summary['error'] = repr(e)
        for i, _ in enumerate(asserts, start=1):
            details.append({
                'problem_id': answer_path.stem,
                'model': model,
                'test_id': i,
                'passed': False,
                'error': f'Runtime setup failure: {repr(e)}'
            })

    return summary, details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--answers-dir', required=True, help='Folder with 1.txt ... 30.txt')
    ap.add_argument('--tests-dir', required=True, help='Folder with 1.txt ... 30.txt')
    ap.add_argument('--model', required=True, help='LLM name, e.g. chatgpt')
    ap.add_argument('--summary-output', default='results_summary.csv')
    ap.add_argument('--details-output', default='results_details.csv')
    args = ap.parse_args()

    answers_dir = Path(args.answers_dir)
    tests_dir = Path(args.tests_dir)

    summary_rows = []
    detail_rows = []

    for answer_path in sorted(answers_dir.glob('*.txt'), key=lambda p: int(p.stem) if p.stem.isdigit() else p.stem):
        test_path = tests_dir / answer_path.name
        if not test_path.exists():
            summary_rows.append({
                'problem_id': answer_path.stem,
                'model': args.model,
                'difficulty': '',
                'answer_file': answer_path.name,
                'test_file': answer_path.name,
                'passed': False,
                'tests_passed': 0,
                'tests_total': 0,
                'tests_passed_pct': 0.0,
                'loc': count_loc(strip_fences(answer_path.read_text(encoding='utf-8', errors='ignore'))),
                'error': f'Missing test file: {test_path.name}'
            })
            continue

        summary, details = evaluate_one(answer_path, test_path, args.model)
        summary_rows.append(summary)
        detail_rows.extend(details)

    with Path(args.summary_output).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'problem_id', 'model', 'difficulty', 'answer_file', 'test_file',
            'passed', 'tests_passed', 'tests_total', 'tests_passed_pct', 'loc', 'error'
        ])
        writer.writeheader()
        writer.writerows(summary_rows)

    with Path(args.details_output).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['problem_id', 'model', 'test_id', 'passed', 'error'])
        writer.writeheader()
        writer.writerows(detail_rows)

    print(f'Saved {len(summary_rows)} summary rows to {args.summary_output}')
    print(f'Saved {len(detail_rows)} detail rows to {args.details_output}')


if __name__ == '__main__':
    main()
