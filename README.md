# RunTracker

Вебзастосунок для бігунів: індивідуальні плани підготовки до 5 км / 10 км / півмарафону,
аналітика темпу та пульсових зон, облік зносу бігових кросівок із попередженням про заміну.

Проєкт створений як навчальна кодова база для дисципліни **«Інженерія якості та супровід
програмних систем»** — у ньому свідомо є що вимірювати, що ламати й що рефакторити.
Покрокова інструкція до лабораторної роботи №1: [`docs/LAB1_GUIDE.md`](docs/LAB1_GUIDE.md).

## Стек

| Шар | Технологія |
|---|---|
| Бекенд | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| База даних | PostgreSQL (у Docker) або SQLite (за замовчуванням локально) |
| Фронтенд | Vue 3 (CDN, без збірки), нативний CSS |
| Тести | pytest + pytest-cov |
| Якість | SonarCloud / SonarQube Community, GitHub Actions |

Обсяг кодової бази: ~1100 рядків (≈900 Python + ≈200 JS), 30 юніт- і смоук-тестів.

## Що вміє застосунок

- **Профіль бігуна** — вік, пульс спокою, рівень, тижневий обсяг, історія травм.
- **Щоденник тренувань** — дистанція, час, пульс, тип тренування, автоматичний розрахунок темпу.
- **Пульсові зони** — оцінка максимального пульсу за формулою Танаки, 5 зон за методом Карвонена.
- **Плани підготовки** — генерація потижневого плану з фазами build / recovery / taper.
- **Прогноз результату** — формула Рігеля + рівномірна розкладка по кілометрах.
- **Знос екіпірування** — ліміт пробігу пари з поправкою на травми, обсяг і рівень бігуна;
  статуси `ok → warning → critical → replace`.
- **Аналітика** — тижневі обсяги, тренувальне навантаження, динаміка, особисті рекорди.

## Швидкий старт (SQLite, без Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py                 # демо-бігун, 28 тренувань, 3 пари кросівок
uvicorn app.main:app --reload
```

Відкрити <http://127.0.0.1:8000> — інтерфейс, <http://127.0.0.1:8000/docs> — Swagger.

## Запуск із PostgreSQL

```bash
docker compose up -d db
export DATABASE_URL="postgresql+psycopg2://runtracker:runtracker@localhost:5432/runtracker"
cd backend && python seed.py && uvicorn app.main:app --reload
```

## Тести та покриття

```bash
cd backend
pytest                                        # 30 тестів
pytest --cov=app --cov-report=xml:coverage.xml   # звіт для Sonar
```

## Структура

```
runtracker/
├── backend/
│   ├── app/
│   │   ├── main.py              точка входу FastAPI
│   │   ├── config.py            налаштування з env
│   │   ├── database.py          engine, сесії, init_db
│   │   ├── models.py            Runner, Run, Shoe, TrainingPlan
│   │   ├── schemas.py           Pydantic-схеми
│   │   ├── routers/             HTTP-шар: runners, runs, shoes, plans
│   │   └── services/            бізнес-логіка: pace, heart_rate, gear, plans, analytics
│   ├── tests/                   pytest
│   └── seed.py                  демо-дані
├── frontend/                    index.html + js/ + css/ (Vue 3 з CDN)
├── docs/
│   ├── LAB1_GUIDE.md            інструкція до лабораторної №1
│   ├── refactoring/             версії «ПІСЛЯ» для Завдання 4
│   └── violations/              готові порушення для Завдання 3
├── sonar-project.properties
├── docker-compose.yml           PostgreSQL + опційно SonarQube
└── .github/workflows/sonar.yml  CI: тести + сканування
```

## Основні ендпоїнти

| Метод | Шлях | Призначення |
|---|---|---|
| `GET` | `/api/health` | перевірка стану сервісу |
| `POST` / `GET` | `/api/runners` | створення та перелік бігунів |
| `GET` | `/api/runners/{id}/zones` | пульсові зони за Карвоненом |
| `POST` / `GET` | `/api/runs` | запис і перелік тренувань |
| `GET` | `/api/runs/summary/weekly` | тижневі зведення |
| `GET` | `/api/runs/summary/insights` | динаміка обсягу та особисті рекорди |
| `POST` / `GET` | `/api/shoes` | облік кросівок |
| `GET` | `/api/shoes/{id}/status` | знос пари та рекомендація |
| `POST` | `/api/plans` | генерація плану підготовки |
| `GET` | `/api/plans/race/forecast` | прогноз часу на дистанції + спліти |

## Свідомо залишений технічний борг

Два методи навмисно написані «драбинкою» вкладених умов — це матеріал для Завдання 4:

- `app/services/plans.py → generate_training_plan()`
- `app/services/gear.py → check_equipment_status()`

Рефакторені версії обох лежать у `docs/refactoring/` і проходять ті самі 30 тестів без змін.
