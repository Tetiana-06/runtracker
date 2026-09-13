#!/usr/bin/env bash
# Локальний запуск застосунку: http://127.0.0.1:8000
set -e
cd "$(dirname "$0")/../backend"
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --port 8000
