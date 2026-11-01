# Лабораторна робота №7
## Інформаційна складність за Чепіним та автоматизоване виявлення критичних зон (Hotspots) у хмарному CI/CD

**Проєкт:** RunTracker (Python / FastAPI) · **Гілка:** `metrics_lab7` · **Інструменти:** Radon 6.0.1, pytest, Git CLI, GitHub Actions

> **Простими словами про всю лабу.**
> Мак-Кейб рахує «розвилки» в коді (if, for). Але метод може бути зовсім без розвилок і все одно бути небезпечним,
> якщо в ньому багато змінних, які хтось перезаписує. **Чепін** рахує саме це: скільки змінних і яку роль вони грають.
> Ми (1) порахували Чепіна для одного методу, (2) показали реальний баг через змінювані дані та виправили його
> незмінними об'єктами, (3) налаштували хмарну перевірку, яка сама знаходить «гарячі» файли: складні й часто змінювані.

---

# Сторінка 1. Декларація об'єкта аналізу

| Параметр | Значення |
|---|---|
| Метод | `get_weather_with_resilience(target_url)` |
| Файл | `backend/app/services/weather_client.py` |
| Архітектурний контур | **Інтеграційний** — виклик стороннього REST API (Open-Meteo) |
| Роль у системі | Отримує погоду для адаптації плану тренувань. Має Retry (2 спроби), Exponential Backoff і Fallback (аварійні дані, якщо API недоступний) |
| Хто викликає | `GET /plans/weather-plan` у `backend/app/routers/plans.py` |
| CC за Мак-Кейбом (до) | **5 (A)** — `radon cc -s` → `F 26:0 get_weather_with_resilience - A (5)` |
| Чому саме він | CC ≤ 5 (лінійний, «простий» за Мак-Кейбом), але інтенсивно працює з даними: аргумент, 4 глобальні налаштування, відповідь API, словник результату, лічильник спроб |

Код методу **до** рефакторингу (коміт `e8272d8`):
```python
def get_weather_with_resilience(target_url: str = WEATHER_API_URL) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Спроба %d звернення до погодного сервісу...", attempt)
            response = httpx.get(target_url, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                data["is_fallback"] = False
                return data
            logger.warning("Зовнішній сервіс повернув HTTP %d", response.status_code)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("Спроба %d не вдалася: %s", attempt, exc)

        if attempt < MAX_RETRIES:
            sleep_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
            time.sleep(sleep_time)

    logger.error("Усі %d спроби вичерпано. Перехід на аварійний Fallback.", MAX_RETRIES)
    return FALLBACK_WEATHER   # глобальний ЗМІНЮВАНИЙ dict
```

> **Простими словами:** метод короткий і розвилок мало (CC = 5), тому Мак-Кейб каже «все добре».
> Але всередині живе 11 різних змінних, і одна з них (`FALLBACK_WEATHER`) — спільний для всіх запитів словник,
> який віддається назовні «як є». Це і є прихована небезпека, яку Мак-Кейб не бачить.

---

# Сторінка 2. Семантична матриця Чепіна

## Ролі змінних

| Клас | Що означає | Вага |
|---|---|---|
| **P** (вхідні) | лише читаються | 1 |
| **M** (модифіковані) | значення перезаписується | 2 |
| **C** (керуючі) | стоять в умові `if` / `while` / межі циклу | 3 |
| **T** (транзитні) | лише передаються далі в іншу функцію без змін | 0.5 |

Правило пріоритету, якщо ролей кілька: **C → M → P → T** (беремо найважчу).

## Матриця (стан ДО рефакторингу)

| Змінна | Тип даних | Клас | Інженерне обґрунтування ролі | Вага |
|---|---|---|---|---|
| `target_url` | `str` (аргумент) | **T** | без змін передається в `httpx.get(...)` | 0.5 |
| `attempt` | `int` (лічильник циклу) | **C** | змінюється кожну ітерацію (M), але стоїть в умові `if attempt < MAX_RETRIES` → пріоритет C | 3 |
| `response` | `httpx.Response` | **C** | керує рішенням `if response.status_code == 200` | 3 |
| `data` | `dict` | **M** | стан перезаписується: `data["is_fallback"] = False` | 2 |
| `exc` | `Exception` | **T** | лише передається в `logger.warning(...)` | 0.5 |
| `sleep_time` | `float` | **T** | створюється тільки щоб передати в `time.sleep(...)` | 0.5 |
| `MAX_RETRIES` | `int` (конфіг) | **C** | межа циклу `range(1, MAX_RETRIES + 1)` і умова `attempt < MAX_RETRIES` | 3 |
| `INITIAL_BACKOFF` | `float` (конфіг) | **P** | лише читається у формулі паузи | 1 |
| `TIMEOUT_SECONDS` | `float` (конфіг) | **T** | без змін передається в `httpx.get(timeout=...)` | 0.5 |
| `FALLBACK_WEATHER` | `dict` (глобальний, змінюваний) | **P** | у методі лише читається і повертається (але — за посиланням!) | 1 |
| `logger` | `logging.Logger` (службовий) | **P** | службовий об'єкт, лише читається для виклику методів логування | 1 |

Підсумок: **P = 3** (`INITIAL_BACKOFF`, `FALLBACK_WEATHER`, `logger`), **M = 1** (`data`),
**C = 3** (`attempt`, `response`, `MAX_RETRIES`), **T = 4** (`target_url`, `exc`, `sleep_time`, `TIMEOUT_SECONDS`).

## Формульний розрахунок

```
Cch = 1·P + 2·M + 3·C + 0.5·T
Cch = 1·3 + 2·1 + 3·3 + 0.5·4
Cch = 3   + 2   + 9   + 2
Cch = 16
```

**Висновок:** Cch = 16 > 10 — для лінійного методу це індикатор «хаосу в даних».
Найбільший внесок дають 3 керуючі змінні (9 балів) і змінюваний `data`. Ризик дефектів мутації підтверджено
практично на наступній сторінці: спільний `FALLBACK_WEATHER` псується після першого ж «необережного» споживача.

> **Простими словами:** Чепін — це «рахунок за змінні». Змінну, яку тільки читають, тримати в голові легко (1 бал).
> Змінну, яка змінюється (2 бали) чи від якої залежить `if` (3 бали), — важко. 16 балів у методі на 20 рядків — забагато.

---

# Сторінка 3. Звіт про симуляцію збою (FAIL)

## Сценарій

1. Погодний API лежить (`httpx.get` кидає `TimeoutException`) → метод повертає `FALLBACK_WEATHER`.
2. Перший споживач (наприклад, модуль, що адаптує план під спеку) «підправляє» результат під себе:
   `temperature = 45.0`, `is_fallback = False`.
3. Метод повертав **не копію, а сам глобальний словник** → правка записалась у `FALLBACK_WEATHER`.
4. Другий запит отримує вже зіпсовані дані: «спека 45 °C» і ознаку «це справжні дані, не fallback».

**Бізнес-наслідок:** усім наступним бігунам генерується план під неіснуючу спеку, а система ще й
стверджує, що дані реальні — збій логування подій і невалідний бізнес-результат.

## Лістинг краш-тесту (`backend/tests/test_weather_mutation.py`)

```python
def _call_with_api_down() -> dict:
    with patch("httpx.get", side_effect=httpx.TimeoutException("down")), patch("time.sleep"):
        return get_weather_with_resilience(URL)


def test_fallback_is_not_corrupted_by_caller():
    first = _call_with_api_down()
    # Споживач №1 змінює отриманий результат під свої потреби
    first["temperature"] = 45.0
    first["is_fallback"] = False

    second = _call_with_api_down()

    # Споживач №2 має отримати чисті аварійні дані, а не «спеку 45°C»
    assert second["temperature"] == 18.0
    assert second["is_fallback"] is True
```

## Лог запуску (стан FAIL) — `docs/lab7/02_fail_test_log.txt`

Команда: `cd backend && python -m pytest tests/test_weather_mutation.py tests/test_resilience.py -v --tb=short`

```
tests\test_weather_mutation.py F                                         [ 33%]
tests\test_resilience.py .F                                              [100%]

__________________ test_fallback_is_not_corrupted_by_caller ___________________
tests\test_weather_mutation.py:31: in test_fallback_is_not_corrupted_by_caller
    assert second["temperature"] == 18.0
E   assert 45.0 == 18.0
_________________ test_weather_resilience_fallback_on_timeout _________________
tests\test_resilience.py:56: in test_weather_resilience_fallback_on_timeout
    assert result["is_fallback"] is True
E   assert False is True
=========================== short test summary info ===========================
FAILED tests/test_weather_mutation.py::test_fallback_is_not_corrupted_by_caller
FAILED tests/test_resilience.py::test_weather_resilience_fallback_on_timeout
========================= 2 failed, 1 passed in 0.62s =========================
```

**Важливе спостереження:** впав не лише наш тест, а й **старий, ніяк не пов'язаний тест** `test_resilience.py`
з ЛР3 — зіпсований глобальний fallback «протік» між тестами. Це і є типовий дефект мутації:
помилка в одному місці ламає зовсім інше місце.

Коміт: `8590967 feat(audit): simulate data mutation issue, FAIL`

> 📸 Скріншот для Notion: виконайте команду вище на коміті `8590967` (`git checkout 8590967`) і зробіть знімок терміналу.

> **Простими словами:** метод віддав «оригінал документа» замість «ксерокопії». Перший же користувач написав на ньому
> ручкою — і всі наступні отримують уже зіпсований документ.

---

# Розділ 4. Архітектурний кейс «Очищення від хаосу змінних» (PASS)

## Що зроблено

**1. Імутабельність (Immutable Data).** У Python немає `const`/`final`, тому використано:
- `@dataclass(frozen=True)` — після створення поля об'єкта змінити неможливо (`FrozenInstanceError`);
- `types.MappingProxyType` — словник «тільки для читання» (`FALLBACK_WEATHER["x"] = ...` → `TypeError`);
- метод `as_dict()` щоразу повертає **нову копію** (`copy.deepcopy`) — споживач може правити свою копію, оригінал недоторканий.

**2. Value Objects.**

| Value Object | Що в нього зібрано | Що зникло з методу |
|---|---|---|
| `RetryPolicy` | `max_retries`, `initial_backoff`, `timeout_seconds` + логіка `attempts()`, `is_last()`, `backoff()` | `MAX_RETRIES` (C), `INITIAL_BACKOFF` (P), `TIMEOUT_SECONDS` (T), `sleep_time` (T), умова `attempt < MAX_RETRIES` |
| `WeatherSnapshot` | `payload` (read-only) + `is_fallback` + `as_dict()` | `data` (M), `data["is_fallback"] = False`, спільний змінюваний `FALLBACK_WEATHER` |

Одна спроба запиту (`response`, `exc`, логування, пауза) винесена в допоміжну функцію `_fetch_once`.

## Порівняльна матриця коду (До / Після)

**До** (Cch = 16, CC = 5):
```python
def get_weather_with_resilience(target_url: str = WEATHER_API_URL) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.get(target_url, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                data["is_fallback"] = False      # мутація
                return data
            ...
        except (...) as exc:
            ...
        if attempt < MAX_RETRIES:
            sleep_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
            time.sleep(sleep_time)
    return FALLBACK_WEATHER                      # спільний змінюваний dict
```

**Після** (Cch = 6, CC = 3):
```python
@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = MAX_RETRIES
    initial_backoff: float = INITIAL_BACKOFF
    timeout_seconds: float = TIMEOUT_SECONDS

    def attempts(self) -> range:
        return range(1, self.max_retries + 1)

    def is_last(self, attempt: int) -> bool:
        return attempt >= self.max_retries

    def backoff(self, attempt: int) -> float:
        return self.initial_backoff * (2 ** (attempt - 1))


@dataclass(frozen=True)
class WeatherSnapshot:
    payload: Mapping[str, Any]
    is_fallback: bool

    def as_dict(self) -> dict:
        return {**copy.deepcopy(dict(self.payload)), "is_fallback": self.is_fallback}


FALLBACK_WEATHER = MappingProxyType({...})          # read-only
FALLBACK_SNAPSHOT = WeatherSnapshot(payload=FALLBACK_WEATHER, is_fallback=True)


def get_weather_with_resilience(target_url: str = WEATHER_API_URL,
                                policy: RetryPolicy = DEFAULT_POLICY) -> dict:
    for attempt in policy.attempts():
        snapshot = _fetch_once(target_url, attempt, policy)
        if snapshot:
            return snapshot.as_dict()
    return FALLBACK_SNAPSHOT.as_dict()
```

Зовнішній контракт не змінився: метод, як і раніше, повертає `dict`, тож роутер `/plans/weather-plan` і старі тести працюють без змін.

## Нова матриця Чепіна (стан ПІСЛЯ)

| Змінна | Тип даних | Клас | Інженерне обґрунтування ролі | Вага |
|---|---|---|---|---|
| `target_url` | `str` (аргумент) | **T** | без змін передається в `_fetch_once` | 0.5 |
| `policy` | `RetryPolicy` (frozen VO) | **P** | лише читається (`policy.attempts()`), змінити неможливо | 1 |
| `attempt` | `int` | **T** | береться з незмінного `range`, у тілі не перезаписується, лише передається в `_fetch_once` | 0.5 |
| `snapshot` | `WeatherSnapshot \| None` | **C** | єдина умова: `if snapshot` | 3 |
| `FALLBACK_SNAPSHOT` | `WeatherSnapshot` (frozen VO) | **P** | лише читається, повертається копією | 1 |

Підсумок: **P = 2, M = 0, C = 1, T = 2**.

```
Cch = 1·P + 2·M + 3·C + 0.5·T
Cch = 1·2 + 2·0 + 3·1 + 0.5·2
Cch = 2   + 0   + 3   + 1
Cch = 6
```

| Показник | До | Після | Зміна |
|---|---|---|---|
| Кількість змінних | 11 | 5 | −55% |
| M (модифіковані) | 1 | **0** | мутацій немає |
| C (керуючі) | 3 | 1 | −67% |
| **Cch** | **16** | **6** | **у 2.67 раза менше** |
| CC (Radon) | 5 | 3 | `F 89:0 get_weather_with_resilience - A (3)` |

**Cch = 6 ≤ 6 → еталон чистої функції досягнуто, падіння 16 / 6 = 2.67 ≥ 2 → PASS.**

Чесне зауваження: частина роботи переїхала в `_fetch_once` (CC = 4). Вона не перезаписує жодної змінної (M = 0),
тобто весь модуль тепер вільний від мутацій, і кожна функція має CC ≤ 4.

## Лог тестів (стан PASS) — `docs/lab7/03_pass_test_log.txt`

```
tests\test_weather_mutation.py ..                                        [ 50%]
tests\test_resilience.py ..                                              [100%]

============================== 4 passed in 0.44s ==============================
```
Повний набір backend-тестів: **51 passed** (`cd backend && python -m pytest`).

Додатковий тест `test_value_objects_are_read_only` доводить, що захист працює:
`DEFAULT_POLICY.max_retries = 100` → `FrozenInstanceError`, `FALLBACK_WEATHER["temperature"] = 45` → `TypeError`.

Коміт: `d6d406e refactor(audit): reduce Chapin complexity using immutable Value Objects, PASS`

> 📸 Скріншот для Notion: `cd backend && python -m pytest tests/test_weather_mutation.py tests/test_resilience.py -v` (зелений результат).

## Git History (FAIL → PASS)

Команда: `git log --oneline --graph -16`
```
* 136dcb1 chore(churn-sim): synthetic change 10/10 in tracker/analytics.py
* ...     (ще 9 комітів churn-sim, див. Розділ 6)
* a904d96 chore(audit): add churn simulation script (lab7, variant 2)
* dc29f67 ci(audit): add Hotspots pipeline (radon JSON + git churn -> build artifact)
* d6d406e refactor(audit): reduce Chapin complexity using immutable Value Objects, PASS
* 8590967 feat(audit): simulate data mutation issue, FAIL
* e8272d8 refactor: replace nested conditions in session_intensity with lookup table
```

> 📸 Скріншот для Notion: вивід `git log --oneline --graph -16` або вкладка Git Graph у VS Code.

> **Простими словами:** ми замінили «оригінали документів» на «ламіновані картки»: їх можна прочитати й скопіювати,
> але написати на них не можна. Плюс склали дрібні налаштування в одну «коробку» (`RetryPolicy`), тому метод
> більше не тримає в голові 11 речей — лише 5.

---

# Розділ 5. Код автоматизації CI/CD

Файл `.github/workflows/hotspots.yml` (запускається на кожен Push і Pull Request у будь-яку гілку):

```yaml
name: Hotspots Audit

on:
  push:
  pull_request:

jobs:
  hotspots:
    name: Складність + Churn -> Hotspots
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # повна історія Git потрібна для підрахунку комітів

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Встановити CLI-сканер складності
        run: pip install radon==6.0.1

      - name: Сканування складності (JSON)
        run: |
          mkdir -p reports
          radon cc -j backend/app tracker > reports/cc.json
          radon hal -j backend/app tracker > reports/hal.json

      - name: Code Churn за 90 днів (git log)
        run: |
          git log --since="90 days ago" --format=format: --name-only \
            | grep -v '^$' | sort | uniq -c | sort -nr > reports/churn.txt
          head -20 reports/churn.txt

      - name: Побудова матриці Hotspots
        run: python scripts/hotspots.py reports | tee -a "$GITHUB_STEP_SUMMARY"

      - name: Зберегти звіт як артефакт збірки
        uses: actions/upload-artifact@v4
        with:
          name: hotspots-report
          path: reports/
```

Що робить кожен крок:
1. `checkout` з `fetch-depth: 0` — без повної історії `git log` побачив би лише 1 коміт.
2. Встановлює Radon (CLI-сканер) у хмарному Ubuntu-раннері.
3. Сканує весь код і зберігає **JSON**: `cc.json` (Мак-Кейб), `hal.json` (Холстед).
4. Рахує Churn командою `git log`.
5. `scripts/hotspots.py` зводить усе в `hotspots.json` / `hotspots.csv` і друкує таблицю в Summary збірки.
6. `upload-artifact` — папка `reports/` прикріплюється до збірки як артефакт **hotspots-report**.

Правила класифікації в `scripts/hotspots.py`:
```python
HIGH_CC = 10          # CC > 10 — складний метод (поріг Мак-Кейба)
HIGH_EFFORT = 2000    # E > 2000 — «важкий» файл за Холстедом (верхня чверть проєкту, ЛР6)
HIGH_CHURN = 4        # >= 4 комітів за 90 днів — файл часто змінюється
# складний = max CC > 10 АБО Effort > 2000
```

> 📸 Скріншот для Notion: GitHub → вкладка **Actions** → запуск **Hotspots Audit** (зелена галочка, Job Success)
> → внизу сторінки блок **Artifacts → hotspots-report**. Для цього потрібно запушити гілку: `git push -u origin metrics_lab7`.

> **Простими словами:** це «робот-перевіряльник» у хмарі GitHub. Після кожного push він сам ставить сканер,
> міряє складність, дивиться історію комітів і кладе готовий звіт у «вкладення» до збірки.

---

# Розділ 6. Лог метрик процесу (Code Churn)

Історія проєкту коротка (26 комітів за семестр), тому використано комбінацію:
- **Варіант 1 (ретроспективний аудит)** — реальна історія з ЛР1–ЛР7;
- **Варіант 2 (штучне наповнення)** — 10 технічних комітів у `tracker/analytics.py`, щоб продемонструвати червону зону.

Скрипт `scripts/simulate_churn.sh`:
```bash
FILE=${1:-tracker/analytics.py}
grep -q "^# churn-sim:" "$FILE" || printf '\n# churn-sim: 0\n' >> "$FILE"
for i in $(seq 1 10); do sed -i "s/^# churn-sim: .*/# churn-sim: $i/" "$FILE"; git commit -q -m "chore(churn-sim): synthetic change $i/10 in $FILE" -- "$FILE"; done
```

Команда Churn (90 днів):
```bash
git log --since="90 days ago" --format=format: --name-only | egrep -v '^$' | sort | uniq -c | sort -nr
```

Вивід (`docs/lab7/05_churn_90d.txt`, перші 15 рядків):
```
     12 tracker/analytics.py
      6 backend/app/services/plans.py
      5 sonar-project.properties
      4 backend/app/services/pace.py
      2 docs/violations/02_duplicated_block.py
      2 docs/violations/01_new_code_violations.py
      2 backend/tests/test_weather_mutation.py
      2 backend/app/services/weather_client.py
      2 backend/app/services/report_export_json.py
      2 backend/app/services/report_export_csv.py
      2 backend/app/services/notifications.py
      2 backend/app/services/gear.py
      2 backend/app/routers/plans.py
      2 .gitignore
      2 .github/workflows/build.yml
```
(`tracker/analytics.py`: 2 реальні коміти + 10 штучних = 12.)

> **Простими словами:** Churn — це «скільки разів файл правили». Файл, який правлять постійно, — місце,
> де найчастіше з'являються нові баги.

---

# Розділ 7. Синергетична матриця Hotspots

| Файл | max CC | Effort (Холстед) | Комітів (90 днів) | Категорія ризику |
|---|---|---|---|---|
| `tracker/analytics.py` | 6 | **3104.1** | **12** | 🔴 **Hotspot** |
| `backend/app/privacy/sanitizer.py`* | **11** | **2352.4** | 0 | 🟡 **Sleeping** |
| `backend/app/privacy/service.py`* | **14** | 532.5 | 0 | 🟡 **Sleeping** |
| `backend/app/services/plans.py` | 6 | 1421.7 | **6** | 🟢 **Active** |
| `backend/app/services/pace.py` | 3 | 1000.4 | **4** | 🟢 **Active** |
| `backend/app/services/gear.py` | 5 | 1076.9 | 2 | ⚪ **Stable** |
| `backend/app/services/weather_client.py` | 4 | 225.2 | 2 | ⚪ **Stable** |
| `backend/app/services/heart_rate.py` | 7 | 1383.8 | 1 | ⚪ **Stable** |

\* модулі `backend/app/privacy/*` є в робочій копії, але ще не закомічені (0 комітів), тому взяті з локального
запуску того ж скрипта. У хмарному артефакті вони з'являться після коміту. Повна таблиця — `docs/lab7/hotspots.md`,
машиночитані версії — `docs/lab7/hotspots.json`, `docs/lab7/hotspots.csv`.

## Аналіз

- 🔴 **Hotspot — `tracker/analytics.py`**: найвищий Effort у проєкті (3104) і найчастіше змінюється.
  До штучного наповнення він був у жовтій зоні (2 коміти) — видно, як «спляча загроза» перетворюється на
  головну зону ризику, щойно в неї починають активно комітити. Рекомендація: перед новими змінами розбити
  на дрібніші модулі (як зроблено з `process_run_workout` у ЛР3).
- 🟡 **Sleeping — `privacy/service.py` (CC 14), `privacy/sanitizer.py` (CC 11)**: заплутаний код, але його поки ніхто не правив.
  Рефакторити — коли прийде новий Change Request на ці модулі.
- 🟢 **Active — `plans.py`, `pace.py`**: змінюються найчастіше з реального коду, але лишаються простими
  (у ЛР6 `plans.py` пройшов рефакторинг Lookup Table: Effort 2664 → 1422). Ідеальний стан.
- ⚪ **Stable — `gear.py`, `weather_client.py`, `heart_rate.py`**: прості й рідко змінюються. `weather_client.py`
  після ЛР7 має Effort лише 225 — рефакторинг Чепіна теж зробив його простішим за Холстедом.

> **Простими словами:** складність сама по собі не страшна, якщо код ніхто не чіпає. І часті зміни не страшні,
> якщо код простий. Небезпечно, коли **обидва** показники високі — саме там найбільше регресійних багів.

---

# Розділ 8. Лог валідації ШІ-Техліда (протокол краш-тесту)

| # | Крок | Очікувано | Фактично | Статус |
|---|---|---|---|---|
| 1 | Baseline: `radon cc -s weather_client.py` | CC ≤ 5 | CC = 5 | ✅ |
| 2 | Чепін до рефакторингу | Cch > 10 | Cch = 16 | ✅ ризик підтверджено |
| 3 | Краш-тест мутації (`test_fallback_is_not_corrupted_by_caller`) | тест падає | `assert 45.0 == 18.0`, + каскадне падіння `test_resilience.py` | ❌ FAIL (як і планувалось) |
| 4 | Коміт FAIL | є в історії | `8590967 feat(audit): simulate data mutation issue, FAIL` | ✅ |
| 5 | Рефакторинг: `frozen dataclass`, `MappingProxyType`, копія в `as_dict()` | M = 0 | M = 0 | ✅ |
| 6 | Чепін після рефакторингу | Cch ≤ 6 і падіння ≥ 2× | Cch = 6, падіння 2.67× | ✅ |
| 7 | Регресія: всі тести backend | 100% зелені | 51 passed | ✅ PASS |
| 8 | Захист від запису (`test_value_objects_are_read_only`) | помилка при записі | `FrozenInstanceError`, `TypeError` | ✅ |
| 9 | Pre-commit hook (radon CC ≤ 10, gitleaks) | PASS | PASS, no leaks found | ✅ |
| 10 | Коміт PASS | є в історії | `d6d406e refactor(audit): ... PASS` | ✅ |
| 11 | CI пайплайн Hotspots | Job Success + артефакт | налаштовано; перевіряється після `git push` | ⏳ |

**Вердикт:** краш-тест пройдено за схемою FAIL → PASS. Мутаційний дефект відтворено, усунуто архітектурно
(а не «латкою»), повторне падіння неможливе — запис у fallback і політику повторів блокується мовою.

---

# Висновки

1. Метод з CC = 5 мав Cch = 16: метрика Мак-Кейба «сліпа» до хаосу даних, Чепін його виявив.
2. Ризик мутації підтвердився реальним багом: спільний fallback псувався й ламав навіть сторонні тести.
3. Immutable Data (`frozen dataclass`, `MappingProxyType`, копії) + Value Objects (`RetryPolicy`, `WeatherSnapshot`)
   знизили Cch 16 → 6 (у 2.67 раза), M → 0, CC 5 → 3, поведінка збережена (51 тест зелений).
4. Хмарний пайплайн GitHub Actions автоматично збирає складність (Radon JSON) і Churn (git log) та
   публікує матрицю Hotspots як артефакт збірки.
5. Матриця показала всі 4 зони; головний Hotspot — `tracker/analytics.py`, кандидати на майбутній рефакторинг — модулі `privacy`.

## Артефакти в репозиторії

| Файл | Призначення |
|---|---|
| `backend/app/services/weather_client.py` | відрефакторений метод + Value Objects |
| `backend/tests/test_weather_mutation.py` | краш-тест мутації + тест read-only |
| `.github/workflows/hotspots.yml` | хмарний пайплайн |
| `scripts/hotspots.py` | злиття складності та churn у матрицю |
| `scripts/simulate_churn.sh` | штучне наповнення історії (Варіант 2) |
| `docs/lab7/*` | логи тестів, CC до/після, churn, hotspots.json/csv/md |
