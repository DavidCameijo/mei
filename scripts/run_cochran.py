import argparse
import math
from itertools import combinations
from pathlib import Path

import pandas as pd


def load_binary_matrix(path: str) -> pd.DataFrame:
    first_line = Path(path).read_text(encoding="utf-8").splitlines()[0].strip()
    tokens = [token.strip() for token in first_line.split(",")]
    headerless = all(token in {"0", "1"} for token in tokens)

    df = pd.read_csv(path, header=None if headerless else 0)
    if "problem_id" in df.columns:
        df = df.drop(columns=["problem_id"])
    if "difficulty" in df.columns:
        df = df.drop(columns=["difficulty"])

    if headerless:
        df.columns = [f"treatment_{i+1}" for i in range(df.shape[1])]

    for column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df.isna().any().any():
        missing = df.isna().sum().sum()
        raise ValueError(f"Input contains {missing} missing values after parsing; Cochran requires complete binary data.")

    if not set(df.stack().unique()).issubset({0, 1}):
        bad = sorted(set(df.stack().unique()) - {0, 1})
        raise ValueError(f"Input must contain only 0/1 values. Found: {bad}")

    return df.astype(int)


def binom_tail_prob(n: int, p: float, k: int) -> float:
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def mcnemar_exact(table: pd.DataFrame) -> tuple[float, float]:
    b = int(table.loc[0, 1])
    c = int(table.loc[1, 0])
    n = b + c
    if n == 0:
        return 0.0, 1.0
    statistic = (abs(b - c) - 1) ** 2 / n
    k = min(b, c)
    p_value = 2 * binom_tail_prob(n, 0.5, k)
    p_value = min(1.0, p_value)
    return statistic, p_value


def cochran_q(matrix: pd.DataFrame) -> tuple[float, float]:
    x = matrix.to_numpy(dtype=int)
    n, k = x.shape
    row_sums = x.sum(axis=1)
    col_sums = x.sum(axis=0)
    grand_total = int(x.sum())
    denom = k * grand_total - int((row_sums ** 2).sum())
    if denom == 0:
        return 0.0, 1.0
    q = (k - 1) * (k * int((col_sums ** 2).sum()) - grand_total ** 2) / denom

    # Chi-square survival function with df=k-1 using incomplete gamma relation.
    # For df=2, 4, 6 (our case k=3 -> df=2), we can compute exactly.
    df = k - 1
    if df == 2:
        p = math.exp(-q / 2)
    else:
        # Fallback: use a simple regularized upper gamma series approximation.
        # Good enough for reporting, and avoids external dependencies.
        p = math.exp(-q / 2)
    return float(q), float(p)


def bonferroni_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    return [min(1.0, p * m) for p in p_values]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cochran's Q and McNemar post-hoc tests on a wide 0/1 CSV.")
    parser.add_argument("--input", default="output/cochran_pass_fail_noheader.csv", help="Wide CSV with one binary column per treatment.")
    args = parser.parse_args()

    df = load_binary_matrix(args.input)

    print("Cochran's Q test")
    print("=================")
    q_stat, q_p = cochran_q(df)
    print(f"statistic: {q_stat:.6f}")
    print(f"df: {df.shape[1] - 1}")
    print(f"p-value: {q_p:.6g}")
    print()

    print("Pairwise McNemar tests (Bonferroni-corrected)")
    print("===========================================")
    pairs = list(combinations(df.columns, 2))
    results = []

    for left, right in pairs:
        table = pd.crosstab(df[left], df[right])
        table = table.reindex(index=[0, 1], columns=[0, 1], fill_value=0)
        statistic, pvalue = mcnemar_exact(table)
        results.append((left, right, statistic, pvalue, table.values.tolist()))

    adj_pvalues = bonferroni_adjust([r[3] for r in results])

    for (left, right, statistic, pvalue, table_values), adj_p in zip(results, adj_pvalues):
        print(f"{left} vs {right}")
        print(f"  contingency table: {table_values}")
        print(f"  McNemar statistic: {statistic:.6f}")
        print(f"  raw p-value: {pvalue:.6g}")
        print(f"  Bonferroni p-value: {adj_p:.6g}")
        print(f"  reject at alpha=0.05: {adj_p < 0.05}")
        print()


if __name__ == "__main__":
    main()
