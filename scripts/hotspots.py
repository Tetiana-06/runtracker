"""ЛР7, Завдання 3: синергетична матриця Hotspots.

Зводить у одну таблицю:
  - складність коду з Radon (max CC по функціях файлу + Halstead Effort файлу);
  - мінливість файлу з Git (кількість комітів за 90 днів, Code Churn).

Використання:
  radon cc -j backend/app tracker > reports/cc.json
  radon hal -j backend/app tracker > reports/hal.json
  git log --since="90 days ago" --format=format: --name-only | grep -v '^$' | sort | uniq -c | sort -nr > reports/churn.txt
  python scripts/hotspots.py reports
Результат: reports/hotspots.json, reports/hotspots.csv та таблиця Markdown у консолі.
"""
import csv
import json
import sys
from pathlib import Path

HIGH_CC = 10          # CC > 10 — складний метод (поріг Мак-Кейба)
HIGH_EFFORT = 2000    # E > 2000 — «важкий» файл за Холстедом (верхня чверть проєкту, ЛР6)
HIGH_CHURN = 4        # >= 4 комітів за 90 днів — файл часто змінюється

CATEGORIES = {
    (True, True): "Hotspot (червона)",
    (True, False): "Sleeping (жовта)",
    (False, True): "Active (зелена)",
    (False, False): "Stable (сіра)",
}


def norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def load_churn(path: Path) -> dict:
    churn = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        count, _, name = line.strip().partition(" ")
        if count.isdigit():
            churn[norm(name)] = int(count)
    return churn


def build_rows(cc: dict, hal: dict, churn: dict) -> list:
    rows = []
    for file, blocks in cc.items():
        if not isinstance(blocks, list) or "test" in file:
            continue
        name = norm(file)
        max_cc = max((b["complexity"] for b in blocks), default=0)
        effort = round(hal.get(file, {}).get("total", {}).get("effort", 0), 1)
        commits = churn.get(name, 0)
        is_complex = max_cc > HIGH_CC or effort > HIGH_EFFORT
        is_hot = commits >= HIGH_CHURN
        rows.append({"file": name, "max_cc": max_cc, "effort": effort,
                     "commits_90d": commits, "category": CATEGORIES[(is_complex, is_hot)]})
    return sorted(rows, key=lambda r: (-r["commits_90d"], -r["effort"]))


def main(out_dir: str) -> None:
    out = Path(out_dir)
    cc = json.loads((out / "cc.json").read_text(encoding="utf-8"))
    hal = json.loads((out / "hal.json").read_text(encoding="utf-8"))
    rows = build_rows(cc, hal, load_churn(out / "churn.txt"))

    (out / "hotspots.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out / "hotspots.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print("| Файл | max CC | Effort | Комітів (90 дн) | Категорія |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| `{r['file']}` | {r['max_cc']} | {r['effort']} | {r['commits_90d']} | {r['category']} |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "reports")
