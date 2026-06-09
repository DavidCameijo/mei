#!/usr/bin/env python3
import argparse
import ast
import csv
import io
import json
import re
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pandas as pd

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    RADON_AVAILABLE = True
except Exception:
    RADON_AVAILABLE = False

FENCE_RE = re.compile(r"```(?:python)?\s*|```", re.IGNORECASE)
IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)
STD_LIB_ALLOW = {
    'math','collections','itertools','functools','heapq','bisect','typing','re','string','datetime','random',
    'statistics','fractions','decimal','sys','os','pathlib','json','csv','io','time','copy','operator','array'
}


def strip_fences(text):
    return FENCE_RE.sub('', text).strip()


def count_loc(code):
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith('#'))


def syntax_ok(code):
    try:
        ast.parse(code)
        return True, ''
    except Exception as e:
        return False, repr(e)


def cyclomatic_complexity(code):
    if not RADON_AVAILABLE:
        return None, None
    try:
        blocks = cc_visit(code)
        if not blocks:
            return 1.0, 1
        vals = [b.complexity for b in blocks]
        return sum(vals) / len(vals), max(vals)
    except Exception:
        return None, None


def maintainability_index(code):
    if not RADON_AVAILABLE:
        return None
    try:
        return float(mi_visit(code, multi=True))
    except Exception:
        return None


def extract_imports(code):
    pkgs = set()
    for a, b in IMPORT_RE.findall(code):
        name = (a or b).split('.')[0]
        pkgs.add(name)
    return sorted(pkgs)


def external_import_count(code):
    imports = extract_imports(code)
    return len([x for x in imports if x not in STD_LIB_ALLOW])


def build_candidate(ns):
    if 'Solution' in ns:
        obj = ns['Solution']()
        methods = [name for name in dir(obj) if not name.startswith('_') and callable(getattr(obj, name))]
        if len(methods) == 1:
            return getattr(obj, methods[0])
    funcs = [k for k, v in ns.items() if callable(v) and not k.startswith('_') and k not in {'check'}]
    preferred = [f for f in funcs if f not in {'print', 'input'}]
    if len(preferred) == 1:
        return ns[preferred[0]]
    if preferred:
        return ns[preferred[0]]
    raise ValueError('No callable candidate found')


def count_asserts_in_check(test_code):
    return len(re.findall(r'^\s*assert\b', test_code, re.MULTILINE))


def run_tests(code, test_code):
    code = strip_fences(code)
    ns = {}
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        exec(code, ns)
        exec(test_code, ns)
        if 'check' not in ns:
            raise ValueError('check(candidate) not found in test code')
        candidate = build_candidate(ns)
        ns['check'](candidate)
    return {
        'code_runs': True,
        'tests_passed': count_asserts_in_check(test_code),
        'tests_total': count_asserts_in_check(test_code),
        'tests_passed_pct': 100.0 if count_asserts_in_check(test_code) else None,
        'error_type': '',
        'error_message': '',
        'stdout_len': len(stdout_buf.getvalue()),
        'stderr_len': len(stderr_buf.getvalue()),
    }


def classify_error(exc):
    name = exc.__class__.__name__
    return name, str(exc)


def safe_read_dataset(path):
    path = Path(path)
    if path.suffix.lower() == '.parquet':
        return pd.read_parquet(path)
    for enc in ('utf-8', 'utf-8-sig', 'cp1252', 'latin1'):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    raise ValueError(f'Could not read dataset: {path}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True, help='CSV or parquet with problem metadata and tests')
    ap.add_argument('--answers-root', required=True, help='Root folder with per-model answer folders')
    ap.add_argument('--models', nargs='+', required=True, help='Model folder names, e.g. chatgpt claude gemini')
    ap.add_argument('--output', default='output/metrics.csv')
    args = ap.parse_args()

    df = safe_read_dataset(args.dataset)
    cols = set(df.columns)
    required_any = {'problem_uid', 'test'}
    missing = [c for c in required_any if c not in cols]
    if missing:
        raise ValueError(f'Missing required dataset columns: {missing}')

    meta_cols = ['problem_uid', 'difficulty']
    rows = []

    for _, prow in df.iterrows():
        problem_id = str(prow['problem_uid'])
        test_code = str(prow['test'])
        difficulty = prow['difficulty'] if 'difficulty' in prow else ''

        for model in args.models:
            answer_path = Path(args.answers_root) / model / f'{problem_id}.txt'
            result = {
                'problem_id': problem_id,
                'model': model,
                'difficulty': difficulty,
                'answer_file_exists': answer_path.exists(),
                'code_runs': False,
                'syntax_ok': False,
                'tests_passed': 0,
                'tests_total': count_asserts_in_check(test_code),
                'tests_passed_pct': 0.0,
                'loc': None,
                'cyclomatic_complexity_avg': None,
                'cyclomatic_complexity_max': None,
                'maintainability_index': None,
                'import_count_total': None,
                'import_count_external': None,
                'error_type': '',
                'error_message': '',
            }

            if not answer_path.exists():
                result['error_type'] = 'MissingAnswerFile'
                result['error_message'] = f'Missing file: {answer_path}'
                rows.append(result)
                continue

            code = answer_path.read_text(encoding='utf-8', errors='ignore')
            code = strip_fences(code)
            result['loc'] = count_loc(code)
            result['import_count_total'] = len(extract_imports(code))
            result['import_count_external'] = external_import_count(code)

            ok, syntax_err = syntax_ok(code)
            result['syntax_ok'] = ok
            avg_cc, max_cc = cyclomatic_complexity(code)
            result['cyclomatic_complexity_avg'] = avg_cc
            result['cyclomatic_complexity_max'] = max_cc
            result['maintainability_index'] = maintainability_index(code)

            if not ok:
                result['error_type'] = 'SyntaxError'
                result['error_message'] = syntax_err
                rows.append(result)
                continue

            try:
                test_result = run_tests(code, test_code)
                result.update(test_result)
            except AssertionError as e:
                result['code_runs'] = True
                result['error_type'] = 'AssertionError'
                result['error_message'] = str(e) or 'One or more asserts failed'
            except Exception as e:
                et, em = classify_error(e)
                result['error_type'] = et
                result['error_message'] = em

            rows.append(result)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f'Saved {len(rows)} rows to {out}')
    print('Radon available:', RADON_AVAILABLE)


if __name__ == '__main__':
    main()
