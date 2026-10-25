"""Сумарні метрики Холстеда по всьому проєкту з JSON-звіту radon."""
import json
import math

data = json.load(open("hal_baseline.json", encoding="utf-8"))
h1 = h2 = N1 = N2 = 0
for rep in data.values():
    t = rep.get("total")
    if t:
        h1 += t["h1"]; h2 += t["h2"]; N1 += t["N1"]; N2 += t["N2"]

n, N = h1 + h2, N1 + N2
V = N * math.log2(n)
D = (h1 / 2) * (N2 / h2)
print(f"files={len(data)} h1={h1} h2={h2} N1={N1} N2={N2}")
print(f"vocabulary={n} length={N} V={V:.2f} D={D:.2f} E={V * D:.2f}")
