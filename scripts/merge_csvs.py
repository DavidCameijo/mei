#!/usr/bin/env python3
"""Merge model stats CSVs and complexity CSVs into a canonical dataset.

Final output columns:
llm, problem_id, difficulty, passed, tests_passed, tests_total,
tests_passed_pct, loc, cyclomatic_complexity, error

Inputs expected:
- Model stats CSVs: <llm>.csv
- Complexity CSVs: <llm>_complexity.csv or <llm>_complexity.csf

Rules:
- llm is derived from the directory name if the file lives in a model subfolder,
    otherwise it is inferred from the stats file name.
- complexity is taken from the per-llm complexity file.
- the rest of the stats come from the per-llm stats CSV.
- difficulty is inferred from numeric problem_id:
    0-10 -> Easy, 10-20 -> Medium, 20-30 -> Hard
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


FINAL_COLUMNS = [
    "problem_id",
    "llm",
    "difficulty",
    "passed",
    "tests_passed",
    "tests_total",
    "tests_passed_pct",
    "loc",
    "cyclomatic_complexity",
    "error",
]


PROBLEM_ID_ALIASES = ["problem_id", "problem_uid", "id"]
PASSED_ALIASES = ["passed"]
TESTS_PASSED_ALIASES = ["tests_passed", "passed_count"]
TESTS_TOTAL_ALIASES = ["tests_total", "total_tests"]
TESTS_PCT_ALIASES = ["tests_passed_pct", "passed_pct", "tests_passed_percent"]
LOC_ALIASES = ["loc", "lines_of_code", "lines"]
ERROR_ALIASES = ["error", "error_message", "error_type"]
LLM_ALIASES = ["llm", "model", "model_name"]

STATS_SUFFIXES = (
    "_summary",
    "_details",
    "_results",
    "_stats",
)


NUM_RE = re.compile(r"\d+")


def read_csv(path: Path) -> List[Dict[str, str]]:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    raise ValueError(f"Could not read CSV: {path}")


def read_header(path: Path) -> List[str]:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return next(csv.reader(f), [])
        except Exception:
            continue
    return []


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def first_nonempty(row: Dict[str, str], aliases: Iterable[str]) -> str:
    for key in aliases:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def passed_to_error(passed: str) -> str:
    value = str(passed).strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return "0"
    if value in {"false", "0", "no", "n"}:
        return "1"
    return ""


def infer_difficulty(problem_id: str) -> str:
    match = NUM_RE.search(str(problem_id))
    if not match:
        return ""
    pid = int(match.group())
    if 0 <= pid <= 10:
        return "Easy"
    if 10 < pid <= 20:
        return "Medium"
    if 20 < pid <= 30:
        return "Hard"
    return ""


def normalize_name(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()
    return [token for token in cleaned.split() if token]


def names_match(llm: str, candidate_stem: str) -> bool:
    llm_tokens = normalize_name(llm)
    cand_tokens = normalize_name(candidate_stem)
    if not llm_tokens or not cand_tokens:
        return False
    return all(token in llm_tokens for token in cand_tokens if token != "complexity")


def extract_llm_from_path(path: Path, base_dir: Path) -> str:
    # Prefer a real model subfolder if present; otherwise infer from the filename.
    if path.parent != base_dir:
        return path.parent.name
    name = path.stem
    for suffix in STATS_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def normalize_rows(rows: List[Dict[str, str]], llm: str, source: Path) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        problem_id = first_nonempty(row, PROBLEM_ID_ALIASES)
        if not problem_id:
            continue

        normalized = {
            "llm": llm,
            "problem_id": problem_id,
            "difficulty": infer_difficulty(problem_id),
            "passed": first_nonempty(row, PASSED_ALIASES),
            "tests_passed": first_nonempty(row, TESTS_PASSED_ALIASES),
            "tests_total": first_nonempty(row, TESTS_TOTAL_ALIASES),
            "tests_passed_pct": first_nonempty(row, TESTS_PCT_ALIASES),
            "loc": first_nonempty(row, LOC_ALIASES),
            "cyclomatic_complexity": "",
            "error": passed_to_error(first_nonempty(row, PASSED_ALIASES)),
        }
        out[problem_id] = normalized
    return out


def find_files(base_dir: Path, suffix: str) -> List[Path]:
    return sorted(p for p in base_dir.rglob(f"*{suffix}") if p.is_file())


def is_stats_file(path: Path) -> bool:
    header = [h.strip().lower() for h in read_header(path)]
    if not header:
        return False
    # A valid stats file should have at least one stats identifier plus problem id.
    has_problem = any(col in header for col in PROBLEM_ID_ALIASES)
    has_stats = (
        any(col in header for col in PASSED_ALIASES)
        and any(col in header for col in TESTS_PASSED_ALIASES)
        and any(col in header for col in TESTS_TOTAL_ALIASES)
    )
    return has_problem and has_stats


def complexity_file_candidates(base_dir: Path, llm: str) -> List[Path]:
    aliases = [llm]
    llm_norm = str(llm).lower()
    if llm_norm.startswith("chatgpt"):
        aliases.append("gpt5_5")
        aliases.append("chatgptv5.5")
    if llm_norm.startswith("claude"):
        aliases.append("claude_4_6")
        aliases.append("claude_sonnet_4_6")
    if llm_norm.startswith("gemini"):
        aliases.append("gemini_v3_flash")

    candidates = []
    for alias in aliases:
        candidates.extend([
            base_dir / f"{alias}_complexity.csv",
            base_dir / f"{alias}_complexity.csf",
            base_dir / alias / f"{alias}_complexity.csv",
            base_dir / alias / f"{alias}_complexity.csf",
        ])

    return candidates


def read_complexity_map(base_dir: Path, llm: str) -> Dict[str, str]:
    candidates = complexity_file_candidates(base_dir, llm)
    if not any(p.exists() for p in candidates):
        # fuzzy fallback for names like claude_sonnet_4_6 -> claude_4_6_complexity.csv
        for path in base_dir.rglob("*complexity*.csv"):
            if names_match(llm, path.stem):
                candidates.append(path)
                break
        for path in base_dir.rglob("*complexity*.csf"):
            if names_match(llm, path.stem):
                candidates.append(path)
                break

    for candidate in candidates:
        if not candidate.exists():
            continue
        rows = read_csv(candidate)
        result: Dict[str, str] = {}
        for row in rows:
            problem_id = first_nonempty(row, PROBLEM_ID_ALIASES + ["file"])
            if not problem_id:
                continue
            # If file column is like "1.txt", strip extension
            if problem_id.endswith(".txt"):
                problem_id = Path(problem_id).stem
            comp = first_nonempty(row, ["cyclomatic_complexity", "complexity", "cyclomatic_complexity_avg", "cyclomatic_complexity_max"])
            result[problem_id] = comp
        return result
    return {}


def merge_stats_and_complexity(stats_map: Dict[str, Dict[str, str]], complexity_map: Dict[str, str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for problem_id in sorted(stats_map.keys(), key=lambda x: int(NUM_RE.search(x).group()) if NUM_RE.search(x) else 10**9):
        row = dict(stats_map[problem_id])
        row["cyclomatic_complexity"] = complexity_map.get(problem_id, "")
        rows.append(row)
    return rows


def choose_best_stats_file(candidates: List[Path]) -> Path:
    # Prefer summary files, then plain llm.csv, then any other stats file.
    def score(path: Path) -> Tuple[int, str]:
        stem = path.stem
        if stem.endswith("_summary"):
            return (0, path.name)
        if stem.count("_summary"):
            return (0, path.name)
        if stem.endswith("_details"):
            return (1, path.name)
        return (2, path.name)

    return sorted(candidates, key=score)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge per-LLM stats and complexity CSVs into a final CSV")
    parser.add_argument("--input-dir", default="output", help="Directory containing per-LLM CSV files")
    parser.add_argument("--output", default="output/merged_results.csv", help="Final merged CSV path")
    parser.add_argument("--stats-suffix", default=".csv", help="Suffix for stats CSVs (default: .csv)")
    args = parser.parse_args()

    base_dir = Path(args.input_dir)
    if not base_dir.exists():
        raise SystemExit(f"Input directory not found: {base_dir}")

    # collect candidate stats files, excluding complexity files
    stats_files = [
        p for p in find_files(base_dir, args.stats_suffix)
        if not p.stem.endswith("_complexity")
        and not p.name.endswith("_complexity.csf")
        and is_stats_file(p)
    ]

    merged_rows: List[Dict[str, str]] = []

    # group stats by llm inferred from the parent directory when possible,
    # otherwise by the filename prefix.
    grouped: Dict[str, List[Path]] = {}
    for path in stats_files:
        if path.stem.endswith("_complexity"):
            continue
        llm = extract_llm_from_path(path, base_dir)
        grouped.setdefault(llm, []).append(path)

    for llm, paths in sorted(grouped.items()):
        stats_path = choose_best_stats_file(paths)
        stats_rows = read_csv(stats_path)
        stats_map = normalize_rows(stats_rows, llm=llm, source=stats_path)
        complexity_map = read_complexity_map(base_dir, llm)
        merged_rows.extend(merge_stats_and_complexity(stats_map, complexity_map))

    # fallback: also look for stats files directly under base_dir if no subdir grouping matched
    if not merged_rows:
        for path in sorted(base_dir.glob("*.csv")):
            if path.stem.endswith("_complexity") or not is_stats_file(path):
                continue
            llm = extract_llm_from_path(path, base_dir)
            stats_rows = read_csv(path)
            stats_map = normalize_rows(stats_rows, llm=llm, source=path)
            complexity_map = read_complexity_map(base_dir, llm)
            merged_rows.extend(merge_stats_and_complexity(stats_map, complexity_map))

    # final dedupe by llm + problem_id
    deduped: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in merged_rows:
        key = (row["llm"], row["problem_id"])
        deduped[key] = row

    final_rows = list(deduped.values())
    final_rows.sort(key=lambda r: (int(NUM_RE.search(r["problem_id"]).group()) if NUM_RE.search(r["problem_id"]) else 10**9, r["llm"]))

    write_csv(Path(args.output), final_rows)
    print(f"Wrote {len(final_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
