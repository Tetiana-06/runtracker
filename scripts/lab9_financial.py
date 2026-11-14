"""Lab 9: Software Economics simulator (Principal, Cost of Delay, NPV).

Usage (PowerShell):
    $env:HOURLY_RATE="40"; $env:OVERLOAD_COEFF="1.3"; $env:DISCOUNT_RATE="0.01"
    python scripts/lab9_financial.py docs/lab9/report.json
"""
import json
import os
import sys

report_path = sys.argv[1] if len(sys.argv) > 1 else "docs/lab9/report.json"

HOURLY_RATE = float(os.environ.get("HOURLY_RATE", "40"))
OVERLOAD_COEFF = float(os.environ.get("OVERLOAD_COEFF", "1.3"))
DISCOUNT_RATE = float(os.environ.get("DISCOUNT_RATE", "0.01"))

with open(report_path, encoding="utf-8") as f:
    component = json.load(f)["component"]

measures = {m["metric"]: float(m["value"]) for m in component["measures"]}
sqale_index = measures["sqale_index"]
ncloc = measures["ncloc"]

principal = sqale_index / 60 * HOURLY_RATE * OVERLOAD_COEFF
cost_of_delay = ncloc / 100 * HOURLY_RATE

rows = []
discounted_sum = 0.0
payback_month = None
for t in range(1, 7):
    factor = 1 / (1 + DISCOUNT_RATE) ** t
    profit = cost_of_delay * factor
    discounted_sum += profit
    npv = discounted_sum - principal
    if npv > 0 and payback_month is None:
        payback_month = t
    rows.append((t, factor, profit, npv))

status = "PASS" if payback_month else "FAIL"

lines = [
    "# SOFTWARE ECONOMICS & FINANCIAL QUALITY LEDGER",
    "",
    "## 1. Вхідні параметри аудиту (System Baseline)",
    f"- Проєкт (Key): `{component['key']}`",
    f"- Масштаб системи (NCLOC): {ncloc:,.0f}",
    f"- Початковий технічний борг (SQALE Index): {sqale_index:,.0f} хв",
    f"- HOURLY_RATE = ${HOURLY_RATE}, OVERLOAD_COEFF = {OVERLOAD_COEFF}, DISCOUNT_RATE = {DISCOUNT_RATE}",
    "",
    "## 2. Капіталізація інвестиційних маркерів",
    f"- Тіло боргу (вартість рефакторингу): ${principal:,.2f}",
    f"- Щомісячні збитки від бездіяльності (Cost of Delay): ${cost_of_delay:,.2f}",
    "",
    "## 3. Динаміка окупності інвестицій (6 місяців)",
    "",
    "| Місяць | Коеф. дисконтування | Щомісячний прибуток, $ | Кумулятивний NPV, $ |",
    "|---|---|---|---|",
]
for t, factor, profit, npv in rows:
    lines.append(f"| {t} | {factor:.4f} | {profit:,.2f} | {npv:,.2f} |")

lines += ["", "## 4. Фінальний інженерно-економічний вердикт"]
if payback_month:
    lines.append(f"Точка виходу в нуль (Payback Period): окупність настане на {payback_month} місяці.")
else:
    lines.append("WARNING: борг занадто великий, рефакторинг не окупається за 6 місяців.")
lines += ["", f"## 5. СТАТУС ВОРІТ ЯКОСТІ (Quality Gate): **{status}**", ""]

with open("FINANCIAL_LEDGER.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Principal = ${principal:,.2f}; Cost of Delay = ${cost_of_delay:,.2f}/month")
for t, factor, profit, npv in rows:
    print(f"  month {t}: NPV = ${npv:,.2f}")
print(f"Quality Gate: {status} (payback month: {payback_month})")
print("[OK] FINANCIAL_LEDGER.md successfully generated")
