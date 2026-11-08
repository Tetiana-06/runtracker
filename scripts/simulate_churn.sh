#!/usr/bin/env bash
# ЛР7, Завд.3, Варіант 2: штучне наповнення історії (10 комітів у один файл)
FILE=${1:-tracker/analytics.py}
grep -q "^# churn-sim:" "$FILE" || printf '\n# churn-sim: 0\n' >> "$FILE"
for i in $(seq 1 10); do sed -i "s/^# churn-sim: .*/# churn-sim: $i/" "$FILE"; git commit -q -m "chore(churn-sim): synthetic change $i/10 in $FILE" -- "$FILE"; done
