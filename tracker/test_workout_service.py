"""
Модуль регресійного тестування (Safety Net Regression Tests) для сервісу аналітики бігу.

Цей тестовий набір створено у межах Лабораторної роботи №3 для виконання вимоги:
"Підготувати захисні тести. Перед структурними змінами переконатися, що поведінка
обраного методу покрита автоматизованими тестами. За потреби додати щонайменше
два тести для основного та граничного сценарію."

Призначення:
Забезпечити 100% збереження вихідної бізнес-поведінки функції `process_run_workout`
під час проведення рефакторингу складності (Cognitive Complexity з 38 до <=15,
Cyclomatic Complexity з 23 до <=10).
"""

import os
import sys
import pytest

# =====================================================================
# НАЛАШТУВАННЯ ШЛЯХІВ ІМПОРТУ (PYTHONPATH)
# =====================================================================
# Додаємо директорію модуля та батьківську директорію до sys.path,
# щоб тести гарантовано запускалися як із кореня репозиторію (через pytest),
# так і безпосередньо з папки tracker без помилок ImportError.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Гнучкий імпорт цільової функції з модуля analytics:
try:
    from tracker.analytics import process_run_workout
except ImportError:
    from analytics import process_run_workout


class TestWorkoutServiceSafetyNet:
    """
    Клас захисних регресійних тестів (Safety Net) для методу process_run_workout.
    Перевіряє всі гілки, граничні умови, виняткові ситуації та розрахунки.
    """

    # -----------------------------------------------------------------
    # ТЕСТ 1: Валідація структури та порожніх вхідних даних
    # -----------------------------------------------------------------
    def test_invalid_input_structure(self):
        """
        Тестування реакції системи на некоректний тип або порожні дані.
        Очікувана поведінка:
        - Повертається словник зі статусом 'pending'
        - До списку 'warnings' додається повідомлення 'Invalid data format'
        - Базовий рахунок 'score' дорівнює 0
        """
        # Сценарій 1.1: Порожній словник (empty dict)
        res_empty = process_run_workout({})
        assert res_empty["status"] == "pending", "Порожній словник повинен залишати статус 'pending'"
        assert "Invalid data format" in res_empty["warnings"], "Має бути попередження 'Invalid data format'"
        assert res_empty["score"] == 0, "Рахунок для порожніх даних має дорівнювати 0"

        # Сценарій 1.2: Передача None замість словника
        res_none = process_run_workout(None)
        assert res_none["status"] == "pending", "Значення None повинно залишати статус 'pending'"
        assert "Invalid data format" in res_none["warnings"], "Має бути попередження про невалідний формат"

        # Сценарій 1.3: Передача списку замість словника
        res_invalid_type = process_run_workout(["некоректні", "дані"])
        assert "Invalid data format" in res_invalid_type["warnings"]

    # -----------------------------------------------------------------
    # ТЕСТ 2: Граничні випадки для дистанції та тривалості
    # -----------------------------------------------------------------
    def test_invalid_distance_or_duration(self):
        """
        Тестування некоректних або недопустимих фізичних показників:
        - Дистанція <= 0 (ділення на нуль або фізично неможлива)
        - Тривалість <= 0
        Очікувана поведінка:
        - Попередження 'Non-positive distance or duration'
        - Статус 'pending', переривання подальших розрахунків
        """
        # Сценарій 2.1: Нульова дистанція (повинна блокувати поділ на 0 при розрахунку темпу)
        res_zero_dist = process_run_workout({"distance": 0, "duration": 120})
        assert "Non-positive distance or duration" in res_zero_dist["warnings"]
        assert res_zero_dist["status"] == "pending"

        # Сценарій 2.2: Від'ємна тривалість тренування
        res_neg_dur = process_run_workout({"distance": 10.0, "duration": -5.0})
        assert "Non-positive distance or duration" in res_neg_dur["warnings"]
        assert res_neg_dur["status"] == "pending"

        # Сценарій 2.3: Обидва параметри від'ємні
        res_both_neg = process_run_workout({"distance": -2.0, "duration": -10.0})
        assert "Non-positive distance or duration" in res_both_neg["warnings"]

    # -----------------------------------------------------------------
    # ТЕСТ 3: Категоризація темпу (Pace Categories) та граничні переходи
    # -----------------------------------------------------------------
    @pytest.mark.parametrize(
        "duration,distance,expected_category,case_description",
        [
            # Спринт: темп < 3.0 хв/км
            (2.9, 1.0, "sprint", "Темп 2.9 хв/км -> суворе входження в категорію sprint"),
            # Границя 3.0 хв/км: перехід у категорію tempo
            (3.0, 1.0, "tempo", "Гранична точка 3.0 хв/км -> початок категорії tempo"),
            (4.49, 1.0, "tempo", "Темп 4.49 хв/км -> верхня межа категорії tempo"),
            # Границя 4.5 хв/км: перехід в аеробну зону
            (4.5, 1.0, "aerobic", "Гранична точка 4.5 хв/км -> початок категорії aerobic"),
            (5.9, 1.0, "aerobic", "Темп 5.9 хв/км -> середина категорії aerobic"),
            # Границя 6.0 хв/км: перехід у відновлювальний біг
            (6.0, 1.0, "recovery", "Гранична точка 6.0 хв/км -> початок категорії recovery"),
            (7.99, 1.0, "recovery", "Темп 7.99 хв/км -> верхня межа категорії recovery"),
            # Границя 8.0 хв/км та більше: ходьба / повільний рух
            (8.0, 1.0, "walking", "Гранична точка 8.0 хв/км -> категорія walking"),
            (10.0, 1.0, "walking", "Темп 10.0 хв/км -> категорія walking"),
        ],
    )
    def test_pace_categories_boundary_conditions(self, duration, distance, expected_category, case_description):
        """
        Перевірка граничних переходів між категоріями темпу (sprint, tempo, aerobic, recovery, walking).
        Розрахунок темпу: pace = duration / distance.
        """
        data = {"distance": distance, "duration": duration}
        result = process_run_workout(data)
        assert result["pace_category"] == expected_category, f"Помилка класифікації: {case_description}"

    # -----------------------------------------------------------------
    # ТЕСТ 4: Пульсові зони серцевого ритму (Heart Rate Zones)
    # -----------------------------------------------------------------
    @pytest.mark.parametrize(
        "heart_rate,expected_zone,case_description",
        [
            (100, "Z1", "Пульс 100 bpm (<120) -> Зона Z1 (відновлення)"),
            (119, "Z1", "Пульс 119 bpm -> верхня межа Z1"),
            (120, "Z2", "Пульс 120 bpm -> нижня межа Z2 (аеробна база)"),
            (144, "Z2", "Пульс 144 bpm -> верхня межа Z2"),
            (145, "Z3", "Пульс 145 bpm -> нижня межа Z3 (аеробний темп)"),
            (164, "Z3", "Пульс 164 bpm -> верхня межа Z3"),
            (165, "Z4", "Пульс 165 bpm -> нижня межа Z4 (анаеробний поріг)"),
            (184, "Z4", "Пульс 184 bpm -> верхня межа Z4"),
            (185, "Z5", "Пульс 185 bpm -> максимальне навантаження Z5"),
            (205, "Z5", "Пульс 205 bpm -> екстремальний Z5"),
        ],
    )
    def test_heart_rate_zones_boundary_conditions(self, heart_rate, expected_zone, case_description):
        """
        Перевірка точного віднесення середнього пульсу до зон навантаження (Z1-Z5).
        """
        data = {
            "distance": 10.0,
            "duration": 50.0,
            "avg_heart_rate": heart_rate,
        }
        result = process_run_workout(data)
        assert result["zones"] == [expected_zone], f"Невідповідність зони пульсу: {case_description}"

    def test_heart_rate_none(self):
        """
        Перевірка сценарію тренування без датчика пульсу (avg_heart_rate відсутній або None).
        Очікувана поведінка: список 'zones' залишається порожнім, виняток не генерується.
        """
        data = {"distance": 5.0, "duration": 25.0, "avg_heart_rate": None}
        result = process_run_workout(data)
        assert result["zones"] == [], "Без пульсометра список зон повинен бути порожнім"

    # -----------------------------------------------------------------
    # ТЕСТ 5: Вплив погодних факторів (Weather Conditions)
    # -----------------------------------------------------------------
    @pytest.mark.parametrize(
        "temperature,humidity,expected_warning,score_penalty,description",
        [
            # Екстремальні умови 1: спека > 30°C і вологість > 70%
            (32, 75, "Extreme weather conditions", -10, "Спека + вологість: штраф -10 балів"),
            # Екстремальні умови 2: мороз < -5°C незалежно від вологості
            (-6, 40, "Extreme weather conditions", -10, "Сильний мороз: штраф -10 балів"),
            # Складні умови 1: температура > 25°C
            (27, 60, "Challenging weather", -5, "Підвищена температура: штраф -5 балів"),
            # Складні умови 2: вологість > 80%
            (20, 85, "Challenging weather", -5, "Висока вологість: штраф -5 балів"),
            # Комфортні умови: нормальна температура та вологість
            (18, 55, None, 0, "Ідеальна погода: без штрафів і попереджень"),
        ],
    )
    def test_weather_impact_and_penalties(self, temperature, humidity, expected_warning, score_penalty, description):
        """
        Перевірка коректності застосування погодних модифікаторів до рейтингу тренування.
        """
        data = {
            "distance": 10.0,
            "duration": 50.0,
            "weather": {"temperature": temperature, "humidity": humidity},
        }
        result = process_run_workout(data)
        if expected_warning is not None:
            assert expected_warning in result["warnings"], f"Має бути попередження про погоду ({description})"
        else:
            assert result["warnings"] == [], f"Для комфортної погоди попередження відсутні ({description})"
        assert result["score"] == score_penalty, f"Неправильний штраф за погоду ({description})"

    # -----------------------------------------------------------------
    # ТЕСТ 6: Розрахунок кілометрових відрізків (Splits) та загального Score
    # -----------------------------------------------------------------
    def test_splits_calculation_and_positive_score(self):
        """
        Перевірка аналізу сплітів (проміжних кілометрів):
        - Якщо split_pace > 0 та split_pace < pace (біг швидший за середній): +2 бали
        - Якщо split_pace >= pace (біг повільніший або рівний середньому): +1 бал
        - Якщо split_pace == 0 (помилковий запис спліту): ігнорується, 0 балів
        """
        # Середній темп тренування: pace = 50.0 / 10.0 = 5.0 хв/км
        workout_data = {
            "distance": 10.0,
            "duration": 50.0,
            "splits": [
                {"duration": 4.8},  # 4.8 < 5.0 (швидший спліт) -> +2 бали
                {"duration": 5.0},  # 5.0 >= 5.0 (рівний спліт)  -> +1 бал
                {"duration": 5.2},  # 5.2 >= 5.0 (повільніший)    -> +1 бал
                {"duration": 0.0},  # 0.0 (некоректний спліт)     -> +0 балів
            ],
        }
        result = process_run_workout(workout_data)
        # Сума очок: 2 + 1 + 1 + 0 = 4 бали
        assert result["score"] == 4, "Загальний рахунок сплітів повинен дорівнювати 4"
        assert result["status"] == "processed", "Статус після успішної обробки має бути 'processed'"

    # -----------------------------------------------------------------
    # ТЕСТ 7: Інтеграційний тест комплексного сценарію
    # -----------------------------------------------------------------
    def test_full_integrated_workout_processing(self):
        """
        Комплексний тест повної обробки типового бігового тренування:
        - Дистанція: 10 км, Час: 48 хв (темп = 4.8 хв/км -> 'aerobic')
        - Пульс: 152 bpm -> 'Z3'
        - Погода: 26°C, 65% -> 'Challenging weather', штраф -5
        - Спліти: [4.5 (<4.8, +2), 4.7 (<4.8, +2), 5.0 (>=4.8, +1)] -> очок за спліти = 5
        - Підсумковий score = -5 + 5 = 0
        - Статус = 'processed'
        """
        data = {
            "distance": 10.0,
            "duration": 48.0,
            "avg_heart_rate": 152,
            "weather": {"temperature": 26, "humidity": 65},
            "splits": [
                {"duration": 4.5},
                {"duration": 4.7},
                {"duration": 5.0},
            ],
        }
        res = process_run_workout(data)
        assert res["status"] == "processed"
        assert res["pace_category"] == "aerobic"
        assert res["zones"] == ["Z3"]
        assert "Challenging weather" in res["warnings"]
        assert res["score"] == 0
