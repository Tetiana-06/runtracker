# Лабораторна робота №9
## SQALE, фінансова капіталізація технічного боргу, FPA & UCP

**Об'єкт аудиту:** Ansible AWX (Python / Django) · **Інструменти:** SonarQube Cloud Web API, curl, Python, Git, Draw.io

Файли лабораторної:
- `docs/lab9/report.json` — сира відповідь SonarQube Cloud API
- `scripts/lab9_financial.py` — фінансовий симулятор
- `FINANCIAL_LEDGER.md` — згенерований леджер
- `docs/lab9/console_run.log` — вивід консолі
- `docs/lab9/labels_use_case.drawio` — UML Use Case діаграма
- `docs/lab9/git_log_labels.txt` — Git-лог підмодуля

---

# Сторінка 1. Картка об'єкта Forensic-аудиту

| Поле | Значення |
|---|---|
| Назва | **AWX** (upstream-проєкт Ansible Automation Platform / Ansible Tower) |
| Призначення | Web UI + REST API для запуску Ansible playbook-ів, керування інвентарями, обліковими даними та розкладами задач |
| Мова / стек | Python, Django, Django REST Framework |
| Репозиторій | https://github.com/ansible/awx |
| SonarQube Cloud | https://sonarcloud.io/project/overview?id=ansible_awx |
| **organization key** | `ansible` |
| **project key** | `ansible_awx` |
| ncloc | 72 727 (≥ 50 000 ✔) |

---

# Сторінка 2. Протокол хмарного REST-виклику

**Запит (curl):**
```bash
curl "https://sonarcloud.io/api/measures/component?component=ansible_awx&metricKeys=sqale_index,ncloc,sqale_rating" -o docs/lab9/report.json
```

- Метод: `GET`
- Ендпоінт: `https://sonarcloud.io/api/measures/component`
- `component=ansible_awx` — ключ проєкту
- `metricKeys=sqale_index,ncloc,sqale_rating` — три метрики SQALE
- Авторизація не потрібна, бо проєкт публічний

**Сира відповідь сервера (`docs/lab9/report.json`):**
```json
{
  "component": {
    "id": "AZDmQK2Oguo2e2_1MUye",
    "key": "ansible_awx",
    "name": "awx",
    "qualifier": "TRK",
    "measures": [
      { "metric": "ncloc",        "value": "72727" },
      { "metric": "sqale_index",  "value": "10614", "bestValue": false },
      { "metric": "sqale_rating", "value": "1.0",   "bestValue": true }
    ]
  }
}
```

**Що зафіксувати в Notion (скріншот / код-блок):**
1. Повний текст команди curl (вище).
2. JSON-відповідь. Окремо виділити три ключі: `ncloc` = 72727, `sqale_index` = 10614 (хвилини), `sqale_rating` = 1.0 (1.0 = A).
3. Дату запиту (2026-11-13), бо значення в хмарі змінюються після кожного нового аналізу.

---

# Сторінка 3. Паспорт технічного боргу (SQALE Audit Ledger)

**Розрахунки:**
- Борг у годинах = 10614 / 60 = **176.9 люд.-год**
- Борг у днях = 176.9 / 8 = **22.11 люд.-днів**
- Обсяг системи в годинах = 72727 × 0.5 = **36 363.5 год**
- TDD = 176.9 / 36 363.5 × 100% = **0.49 %**

| Масштаб (ncloc) | Борг (люд.-год / люд.-днів) | TDD (%) | Хмарний рейтинг (sqale_rating) |
|---|---|---|---|
| 72 727 | 176.9 / 22.11 | 0.49 % | 1.0 = **A** |

**Верифікація:** TDD = 0.49% ≤ 5%, тобто за шкалою SQALE це рейтинг **A**. SonarQube Cloud повернув `sqale_rating = 1.0`, що теж означає A. Мій розрахунок **збігається** з хмарним.

---

# Сторінка 4. Економіка рефакторингу (Financial Quality Ledger)

## 4.1 Вихідний код скрипту (`scripts/lab9_financial.py`)
```python
"""Lab 9: Software Economics simulator (Principal, Cost of Delay, NPV)."""
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
# ... далі формування FINANCIAL_LEDGER.md (див. повний файл у репозиторії)
```
(Повний текст із генерацією markdown є у файлі `scripts/lab9_financial.py`. У Notion вставити його повністю.)

## 4.2 Запуск (зробити скріншот терміналу)
```powershell
$env:HOURLY_RATE="40"; $env:OVERLOAD_COEFF="1.3"; $env:DISCOUNT_RATE="0.01"
python scripts/lab9_financial.py docs/lab9/report.json
```
Вивід:
```
Principal = $9,198.80; Cost of Delay = $29,090.80/month
  month 1: NPV = $19,603.97
  month 2: NPV = $48,121.57
  month 3: NPV = $76,356.81
  month 4: NPV = $104,312.50
  month 5: NPV = $131,991.40
  month 6: NPV = $159,396.25
Quality Gate: PASS (payback month: 1)
[OK] FINANCIAL_LEDGER.md successfully generated
```

## 4.3 Згенерований FINANCIAL_LEDGER.md

- Тіло боргу = 10614 / 60 × 40 × 1.3 = **$9 198.80**
- Cost of Delay = 72727 / 100 × 40 = **$29 090.80 / міс.**

| Місяць | Коеф. дисконтування | Щомісячний прибуток, $ | Кумулятивний NPV, $ |
|---|---|---|---|
| 1 | 0.9901 | 28,802.77 | 19,603.97 |
| 2 | 0.9803 | 28,517.60 | 48,121.57 |
| 3 | 0.9706 | 28,235.24 | 76,356.81 |
| 4 | 0.9610 | 27,955.69 | 104,312.50 |
| 5 | 0.9515 | 27,678.90 | 131,991.40 |
| 6 | 0.9420 | 27,404.85 | 159,396.25 |

**Payback Period:** 1-й місяць. **Quality Gate: PASS.**

## 4.4 Висновок щодо Software Economics
Cost of Delay росте разом з ncloc: що більша система, то більше годин команда щомісяця втрачає на регресійні баги. Тіло боргу залежить тільки від sqale_index. Тому швидкість окупності визначає відношення sqale_index / ncloc, тобто щільність боргу (TDD). В AWX борг низький (0.49%), тому рефакторинг окупається вже за 1 місяць. За нашими формулами рефакторинг не окупиться за 6 місяців, якщо TDD перевищить приблизно 9% (рейтинг B і гірше). У такому разі Quality Gate покаже FAIL, і борг треба гасити частинами.

---

# Сторінка 5. Специфікація реверс-інжиніринг початкових даних

**Обраний підмодуль:** Labels (мітки/теги для Job Templates, Inventories, Schedules, Workflow nodes).

| Файл | Роль |
|---|---|
| `awx/main/models/label.py` | ORM-сутність `Label` |
| `awx/api/views/labels.py` | API-в'юшки `LabelList`, `LabelDetail`, `LabelSubListCreateAttachDetachView` |
| `awx/api/urls/label.py` | маршрути `/api/v2/labels/`, `/api/v2/labels/{id}/` |
| `awx/api/serializers.py` | `LabelSerializer` |
| `awx/main/access.py` | `LabelAccess` (RBAC-перевірки) |

**ORM-сутності (дані):**
- `Label(CommonModelNameNotUnique)`: поля `id, name, description, created, modified, created_by, modified_by, organization (FK)`; `unique_together = (name, organization)`.
- Зовнішні (тільки читання): `Organization` (FK і RBAC-ролі), а також ресурси з мітками `UnifiedJob`, `UnifiedJobTemplate`, `Inventory`, `Schedule`, `WorkflowJobTemplateNode`, `WorkflowJobNode` (читаються у `is_detached()` та `is_candidate_for_detach()`).

**Сигнатури методів / API-ендпоінти (транзакції):**
| Ендпоінт / метод | Клас | Дія |
|---|---|---|
| `GET /api/v2/labels/` | `LabelList` | список міток |
| `POST /api/v2/labels/` | `LabelList` | створити мітку |
| `GET /api/v2/labels/{id}/` | `LabelDetail` | деталі мітки |
| `PUT/PATCH /api/v2/labels/{id}/` | `LabelDetail` | змінити мітку |
| `GET /api/v2/<resource>/{id}/labels/` | `LabelSubListCreateAttachDetachView` | мітки ресурсу |
| `POST /api/v2/<resource>/{id}/labels/` → `post()` | `LabelSubListCreateAttachDetachView` | створити або приєднати мітку (ліміт 100) |
| `POST ... {"disassociate": true}` → `unattach()` | `LabelSubListCreateAttachDetachView` | від'єднати й видалити, якщо мітка ніде більше не використовується |
| `can_add(data)`, `can_change(obj, data)`, `can_delete(obj)` | `LabelAccess` | RBAC |
| `is_detached()`, `is_candidate_for_detach()` | `Label` | перевірка використання |

**Актори:** AWX User (людина через Web UI); API-клієнт (awx CLI / Ansible collection `awx.awx.label`).

**Use Cases:** UC1 Create label, UC2 Edit label, UC3 View/list labels, UC4 Attach label to resource, UC5 Detach label.

**UML Use Case діаграма:** `docs/lab9/labels_use_case.drawio`. Відкрити на app.diagrams.net, експортувати в PNG і вставити в Notion.

```
 AWX User (GUI)                         API client / CLI
      |        +------ AWX Labels ------+      |
      |------- | (UC1 Create label)     | -----|
      |------- | (UC2 Edit label)       | -----|
      |------- | (UC3 View/list labels) | -----|
      |------- | (UC4 Attach label)     | -----|
      |------- | (UC5 Detach label)     | -----|
               +------------------------+
```

**Git-статистика підмодуля** (`git log -- awx/main/models/label.py awx/api/views/labels.py awx/api/urls/label.py`):
- 20 комітів, 10 імен авторів (Chris Meyers 5, Alan Rominger 3, Ryan Petrello 2, John Westcott IV 2, Jeff Bradberry 2, Aaron Tan 2, Wayne Witzel III 1, Seth Foster 1, Alex Corey 1, AlanCoding 1)
- Період розробки: 2016-03-22 → 2026-01-19

---

# Сторінка 6. FPA Калькулятор (IFPUG Ledger)

Ваги IFPUG: ILF 7/10/15, EIF 5/7/10, EI 3/4/6, EO 4/5/7, EQ 3/4/6 (Low/Avg/High).

| № | Елемент | Категорія | Складність | Вага (FP) |
|---|---|---|---|---|
| 1 | `Label` (власна таблиця модуля) | ILF | Low | 7 |
| 2 | `Organization` (тільки читання для FK/RBAC) | EIF | Low | 5 |
| 3 | Ресурси з мітками (JT, Inventory, Schedule, WF nodes, Jobs) | EIF | Low | 5 |
| 4 | Створити мітку `POST /labels/` | EI | Low | 3 |
| 5 | Змінити мітку `PUT/PATCH /labels/{id}/` | EI | Low | 3 |
| 6 | Приєднати/створити мітку на ресурсі (пошук існуючої + ліміт 100) | EI | Average | 4 |
| 7 | Від'єднати мітку + автовидалення | EI | Average | 4 |
| 8 | Список міток `GET /labels/` | EQ | Low | 3 |
| 9 | Деталі мітки `GET /labels/{id}/` | EQ | Low | 3 |
| 10 | Мітки ресурсу `GET /<resource>/{id}/labels/` | EQ | Low | 3 |
| — | Звіти/калькуляції | EO | — | 0 (у модулі немає) |

| Категорія | Кількість | FP |
|---|---|---|
| ILF | 1 | 7 |
| EIF | 2 | 10 |
| EI | 4 | 14 |
| EO | 0 | 0 |
| EQ | 3 | 9 |
| **Разом (UFP)** | 10 | **40 FP** |

---

# Сторінка 7. UCP Матриця Карнера

**Крок 1. Актори (UAW)**
| Актор | Тип | Вага |
|---|---|---|
| API client / awx CLI / Ansible collection | Простий (API/CLI) | 1 |
| AWX User через Web UI | Складний (людина через GUI) | 3 |
| **UAW** | | **4** |

**Крок 2. Use Cases (UUCW)**
| Use Case | Транзакції (кроки) | К-сть | Тип | Вага |
|---|---|---|---|---|
| UC1 Create label | валідація → RBAC `can_add` → збереження | 3 | Простий | 5 |
| UC2 Edit label | валідація → `can_add` → перевірка admin_role → збереження | 4 | Середній | 10 |
| UC3 View/list labels | RBAC-фільтр `filtered_queryset` → пагінація → серіалізація | 3 | Простий | 5 |
| UC4 Attach label | пошук існуючої → підміна id → перевірка ліміту 100 → створення/attach → відповідь | 5 | Середній | 10 |
| UC5 Detach label | `unattach_validate` → `unattach_by_id` → `is_detached()` → `delete()` | 4 | Середній | 10 |
| **UUCW** | | | | **40** |

**Крок 3. Підсумок**
- UUCP = UAW + UUCW = 4 + 40 = **44**
- TCF = 1.0, ECF = 1.0
- **UCP = 44 × 1.0 × 1.0 = 44**

---

# Сторінка 8. Звіт про зворотне калібрування

**Трудовитрати з Git:** 20 комітів у підмодулі. Беру умовну норму 4 люд.-год на коміт (код, рев'ю, тести).
Реальні трудовитрати = 20 × 4 = **80 люд.-год**.

**Productivity Factor:**
PF = 80 / 44 = **1.82 люд.-год на 1 UCP**

**Висновок Lead Engineer:**
PF показує, скільки годин команда реально витрачає на одну точку UCP. Коли замовник присилає Change Request, ми ще до написання коду малюємо Use Case для нової функції, рахуємо UCP і множимо на PF. Наприклад, CR «мітки для Credentials» = 1 новий простий UC (5) + ті самі актори (4) = 9 UCP. Тоді 9 × 1.82 ≈ 16.4 люд.-год, а за ставки $40 × 1.3 це ≈ $851. Так бюджет спирається на історичні дані команди, а не на суб'єктивну «оцінку на око». Ризик зростання обсягу видно відразу: кожен доданий складний UC додає 15 UCP, тобто ≈ 27 год. PF треба перекалібровувати після кожного релізу, бо з часом змінюються команда і кодова база.

---

# Висновки до завдань

## Висновок до Завдання 1 (Forensic-аудит SQALE)
Для аудиту я обрала великий open-source проєкт **Ansible AWX** (`ansible` / `ansible_awx`). Його обсяг 72 727 ncloc, тож умову ≥ 50 000 виконано. Через публічне REST API SonarQube Cloud (`GET /api/measures/component`) я отримала три метрики: `sqale_index`, `ncloc` і `sqale_rating`. Сиру відповідь сервера збережено у `docs/lab9/report.json`. Потім я незалежно перерахувала борг: 10 614 хв = 176.9 люд.-год = 22.11 люд.-днів. Індекс TDD = 176.9 / (72 727 × 0.5) × 100% = **0.49%**. За шкалою SQALE це рейтинг **A** (≤ 5%), і він збігається з хмарним `sqale_rating = 1.0` (A). Отже, хмарний розрахунок об'єктивний. Технічний борг AWX дуже низький відносно розміру системи.

**Чим покрито:** картка об'єкта (сторінка 1), текст curl-запиту і сирий JSON (сторінка 2), таблиця SQALE Audit Ledger з TDD та верифікацією рейтингу (сторінка 3).

## Висновок до Завдання 2 (Software Economics)
Я написала консольний скрипт `scripts/lab9_financial.py` на Python. Він читає `report.json` і змінні оточення `HOURLY_RATE = 40`, `OVERLOAD_COEFF = 1.3`, `DISCOUNT_RATE = 0.01`. Скрипт рахує:
- Тіло боргу: **$9 198.80**;
- Cost of Delay: **$29 090.80 на місяць**;
- кумулятивний NPV у циклі `for t in 1..6` з дисконтуванням.

Умова `if npv > 0` фіксує точку окупності: це **1-й місяць**. Результат скрипт записує у `FINANCIAL_LEDGER.md` (таблиця грошових потоків і статус **PASS**). Окупність настала так швидко, бо щомісячні втрати від бездіяльності, які залежать від ncloc, утричі більші за одноразову вартість рефакторингу, яка залежить від sqale_index. Отже, для великих систем із низькою щільністю боргу рефакторинг окупається майже одразу. Якби TDD перевищив ≈ 9%, скрипт показав би FAIL.

**Чим покрито:** повний код скрипту, команда запуску та консольний вивід (`docs/lab9/console_run.log`, для скріншоту), лістинг `FINANCIAL_LEDGER.md` і аналітичний висновок (сторінка 4).

## Висновок до Завдання 3 (FPA & UCP, зворотне калібрування)
Для аналізу я виділила ізольований підмодуль **Labels** з AWX. До нього входять 5 файлів: модель `Label`, в'юшки `LabelList`, `LabelDetail` і `LabelSubListCreateAttachDetachView`, а також маршрути, серіалізатор і RBAC-клас `LabelAccess`. Початкові дані зібрано з трьох джерел:
- ORM-модель → дані (ILF / EIF);
- API-ендпоінти й сигнатури методів → транзакції та актори;
- Git-лог (20 комітів, 10 авторів) → трудовитрати.

Результати:
- **FPA:** 1 ILF + 2 EIF + 4 EI + 0 EO + 3 EQ = **40 FP**.
- **UCP:** 2 актори (UAW = 4) і 5 Use Cases (UUCW = 40). Звідси UUCP = 44, а за TCF = ECF = 1.0 маємо **UCP = 44**.
- **Зворотне калібрування:** трудовитрати оцінено як 20 комітів × 4 год = 80 люд.-год. Тоді **PF = 80 / 44 ≈ 1.82 люд.-год на 1 UCP**.

Такий PF дозволяє оцінити будь-який Change Request ще до написання коду: рахуємо UCP нової функції і множимо на PF та ставку. Наприклад, CR на 9 UCP ≈ 16.4 год ≈ $851.

**Чим покрито:** специфікація реверс-інжинірингу з сигнатурами, ORM-сутностями, акторами, Use Cases, UML-діаграмою `docs/lab9/labels_use_case.drawio` і Git-статистикою (сторінка 5), FPA-калькулятор (сторінка 6), UCP-матриця Карнера (сторінка 7), звіт про калібрування PF з висновком (сторінка 8).

## Загальний висновок
Під час роботи я пройшла повний цикл оцінювання ПЗ:
1. Отримала метрики SQALE з хмарного API.
2. Незалежно перевірила рейтинг через TDD.
3. Перевела борг у гроші й автоматично порахувала окупність рефакторингу (NPV, Payback Period).
4. Виміряла функціональний розмір модуля незалежно від мови програмування (FPA та UCP).
5. Відкалібрувала продуктивність команди (PF) для прогнозування бюджету майбутніх змін.
