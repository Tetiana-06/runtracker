# RunTracker

Вебзастосунок для бігунів: індивідуальні плани підготовки до 5 км / 10 км / півмарафону, аналітика темпу та пульсових зон, облік зносу бігових кросівок із попередженням про заміну та повний комплаєнс із регламентом GDPR (Privacy by Design).

Проєкт розвивається у межах курсу **«Інженерія якості та супровід програмних систем»**.

---

## Архітектурний паспорт системи

Повна інженерна документація за стандартом Documentation as Code розташована в каталозі `docs/`:
- **[System Design Document (SDD)](docs/sdd.md)**: C4-діаграма контейнерів, декомпозиція сервісів, ER-модель даних та API-контракти.
- **[Infrastructure Specification Document (ISD)](docs/isd.md)**: топологія розгортання (Dev / Compose / Cloud), матриця змінних середовища, CI/CD конвеєр, цільові метрики RTO ($\le 15$ хв) та RPO ($\le 1$ год).
- **[Architecture Decision Records (ADR)](docs/architecture/adr/README.md)**: кущ архітектурних рішень (ADR-0001: Гібридне сховище даних SQLite/PostgreSQL, ADR-0002: Модульний моноліт FastAPI).
- **[Регламент супроводу документації](docs/maintenance.md)**: власники документів, інтервали перегляду та правило «зміна коду = зміна документації».
- **[Пакет передачі знань (Handover Package)](docs/handover.md)**: онбординг, декларація Bus Factor та процедура супроводу.

---

## Технологічний стек

| Шар | Технологія | Призначення |
|---|---|---|
| **Бекенд** | Python 3.12, FastAPI, SQLAlchemy 2.0, Uvicorn | Модульний REST API моноліт, бізнес-калькуляції |
| **База даних** | SQLite (локально / тести) / PostgreSQL 15 (Docker) | Гібридне реляційне сховище (ADR-0001) |
| **Фронтенд** | Vue 3 (CDN, Single Page App), Vanilla JS, CSS3 | Інтерфейс атлета, графіки, дашборд тренувань |
| **Тестування** | pytest, pytest-cov (57 тестів, покриття >80%) | Регресійні, модульні, інтеграційні тести |
| **Безпека & Приватність**| GDPR Sanitizer, PolicyGate, Gitleaks, PII Filter | Захист конфіденційних медичних та персональних даних |
| **CI/CD & Якість** | GitHub Actions, SonarCloud, Radon (CC $\le 10$) | Контроль воріт якості та моніторинг складності |

---

## Ключовий функціонал

- **Профіль бігуна:** збереження антропометричних даних, пульсу спокою та розрахунок зон за Карвоненом.
- **Щоденник забігів:** дистанція, час, автоматичний розрахунок темпу та сплітів за формулою Рігеля.
- **Аналітика навантаження та інтенсивності:** розподіл тренувань за типами (*easy*, *tempo*, *intervals*, *long*), тижневі обсяги та особисті рекорди.
- **Монітор зносу взуття:** статусний автомат пробігу (`ok → warning → critical → replace`).
- **Генератор тренувальних планів:** адаптивна потижнева побудова фаз *Build*, *Recovery* та *Taper*.
- **Privacy by Design:** право на забуття (знеособлення), експорт персональних даних та фільтрація логів.

---

## Швидкий старт (Onboarding Guide)

### 1. Локальний запуск (SQLite, без Docker)

```bash
# Крок 1: Перехід до каталогу бекенду та створення віртуального середовища
cd backend
python -m venv .venv
source .venv/bin/activate       # Для Linux/macOS
# .venv\Scripts\activate        # Для Windows PowerShell

# Крок 2: Інсталяція залежностей
pip install -r requirements.txt

# Крок 3: Наповнення тестовими даними (демо-атлет, 28 тренувань, 3 пари взуття)
python seed.py

# Крок 4: Запуск локального ASGI-сервера
uvicorn app.main:app --reload --port 8000
```

- Вебінтерфейс: <http://127.0.0.1:8000>
- Інтерактивна документація Swagger UI: <http://127.0.0.1:8000/docs>
- Альтернативна OpenAPI-специфікація ReDoc: <http://127.0.0.1:8000/redoc>

---

### 2. Запуск через Docker Compose (PostgreSQL)

```bash
docker compose up -d db
export DATABASE_URL="postgresql+psycopg2://runtracker:runtracker@localhost:5432/runtracker"
cd backend && python seed.py && uvicorn app.main:app --reload
```

---

### 3. Запуск тестів та перевірка якості

```bash
cd backend
# Запуск повного набору 57 тестів
pytest

# Генерація звіту про покриття коду
pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml

# Локальна перевірка цикломатичної складності (границя CC <= 10)
radon cc -s -n C app/
```

---

## Основні API-ендпоїнти

| Метод | Шлях | Призначення | Аудиторія |
|---|---|---|---|
| `GET` | `/api/health` | Перевірка стану системи (Liveness Probe) | DevOps / SRE |
| `POST` / `GET` | `/api/runners` | Створення та перегляд профілів бігунів | Dev / QA |
| `GET` | `/api/runners/{id}/zones` | Пульсові зони за формулою Карвонена | Dev / QA / Бізнес |
| `POST` / `GET` | `/api/runs` | Додавання тренування та журнал забігів | Dev / QA / Бізнес |
| `GET` | `/api/runs/{id}/details` | Детальна аналітика темпу та сплітів | Dev / QA |
| `GET` | `/api/runs/summary/weekly` | Щотижневий зведений кілометраж | Dev / QA / Бізнес |
| `GET` | `/api/runs/summary/insights` | Аналітичні інсайти та особисті рекорди | Dev / QA / Бізнес |
| `GET` | `/api/runs/summary/intensity` | Розподіл навантаження за інтенсивністю (*easy/tempo/intervals/long*) | Dev / QA / Бізнес |
| `POST` / `GET` | `/api/shoes` | Облік кросівок бігуна | Dev / QA / Бізнес |
| `GET` | `/api/shoes/{id}/status` | Розрахунок зносу пари та рекомендація | Dev / QA / Бізнес |
| `POST` | `/api/plans` | Генерація потижневого плану тренувань | Dev / QA / Бізнес |
| `GET` | `/api/plans/race/forecast` | Прогноз фінішного часу за формулою Рігеля| Dev / QA / Бізнес |
| `POST` | `/api/privacy/consent` | Фіксація згоди на обробку PII | Dev / QA / DevOps |
| `GET` | `/api/privacy/export/{runner_id}`| GDPR Data Portability (вивантаження даних) | Dev / QA / DevOps |
| `POST` | `/api/privacy/anonymize/{runner_id}`| GDPR Right to be Forgotten (знеособлення)| Dev / QA / DevOps |
