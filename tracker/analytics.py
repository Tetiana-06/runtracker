# Завдання 1. Вимірюваний рефакторинг коду
# У модулі розрахунку статистики забігів (сервіс аналізу темпу та калорій трекера) створю типовий метод із глибокою вкладеністю

def process_run_workout(workout_data: dict) -> dict:
    result = {
        "status": "pending",
        "zones": [],
        "warnings": [],
        "score": 0,
    }

    # 1. Перевірка наявності та валідності вхідних даних (+4 CC через and/or/if)
    if not workout_data or not isinstance(workout_data, dict):
        result["warnings"].append("Invalid data format")
        return result

    distance = workout_data.get("distance", 0)
    duration = workout_data.get("duration", 0)
    heart_rate = workout_data.get("avg_heart_rate")
    weather = workout_data.get("weather", {})

    if distance <= 0 or duration <= 0:  # +2 CC (if, or)
        result["warnings"].append("Non-positive distance or duration")
        return result

    # 2. Розрахунок та аналіз темпу (+4 CC через elif)
    pace = duration / distance
    if pace < 3.0:
        result["pace_category"] = "sprint"
    elif 3.0 <= pace < 4.5:
        result["pace_category"] = "tempo"
    elif 4.5 <= pace < 6.0:
        result["pace_category"] = "aerobic"
    elif 6.0 <= pace < 8.0:
        result["pace_category"] = "recovery"
    else:
        result["pace_category"] = "walking"

    # 3. Пульсові зони (+4 CC)
    if heart_rate is not None:
        if heart_rate < 120:
            result["zones"].append("Z1")
        elif heart_rate < 145:
            result["zones"].append("Z2")
        elif heart_rate < 165:
            result["zones"].append("Z3")
        elif heart_rate < 185:
            result["zones"].append("Z4")
        else:
            result["zones"].append("Z5")

    # 4. Врахування погодних факторів (+3 CC через and/or)
    temp = weather.get("temperature", 20)
    humidity = weather.get("humidity", 50)

    if (temp > 30 and humidity > 70) or (temp < -5):
        result["warnings"].append("Extreme weather conditions")
        result["score"] -= 10
    elif temp > 25 or humidity > 80:
        result["warnings"].append("Challenging weather")
        result["score"] -= 5

    # 5. Цикл обробки сплітів/кілометрів (+3 CC через for, if)
    splits = workout_data.get("splits", [])
    for split in splits:
        split_pace = split.get("duration", 0)
        if split_pace > 0 and split_pace < pace:
            result["score"] += 2
        elif split_pace >= pace:
            result["score"] += 1

    result["status"] = "processed"
    return result