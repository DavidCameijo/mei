import csv
from pathlib import Path
from radon.complexity import cc_visit

FOLDER = Path("answers/gemini_v3_flash")
OUTPUT_CSV = "gemini_v3_flash_complexity.csv"

rows = []

for i in range(1, 31):
    file_path = FOLDER / f"{i}.txt"

    if not file_path.exists():
        rows.append({
            "file": f"{i}.txt",
            "cyclomatic_complexity": None,
            "error": "file not found"
        })
        continue

    try:
        code = file_path.read_text(encoding="utf-8")
        blocks = cc_visit(code)

        complexity = max((block.complexity for block in blocks), default=0)

        rows.append({
            "file": f"{i}.txt",
            "cyclomatic_complexity": complexity,
            "error": ""
        })

    except Exception as e:
        rows.append({
            "file": f"{i}.txt",
            "cyclomatic_complexity": None,
            "error": str(e)
        })

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["file", "cyclomatic_complexity", "error"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved to {OUTPUT_CSV}")