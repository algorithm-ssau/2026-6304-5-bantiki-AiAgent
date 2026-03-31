import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Загружаем данные о совместимости
def load_compatibility():
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "compatibility.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

compatibility = load_compatibility()

def build_system_prompt(data: dict) -> str:
    return f"""Ты — ИИ-агент по подбору комплектующих для ПК.

Пользователь описывает задачу (игры, монтаж, офис и т.д.) и бюджет.
Ты подбираешь совместимую сборку и объясняешь каждый выбор.

ПРАВИЛА СОВМЕСТИМОСТИ (строго соблюдай):
- Процессор и материнская плата должны иметь одинаковый сокет
- Тип ОЗУ (DDR4/DDR5) должен совпадать с поддерживаемым материнской платой
- Мощность БП должна быть не ниже рекомендованной для выбранной видеокарты

ДОСТУПНЫЕ КОМПЛЕКТУЮЩИЕ:

Сокеты и процессоры:
{json.dumps(data['sockets'], ensure_ascii=False, indent=2)}

Материнские платы:
{json.dumps(data['motherboards'], ensure_ascii=False, indent=2)}

Оперативная память:
{json.dumps(data['ram'], ensure_ascii=False, indent=2)}

Видеокарты:
{json.dumps(data['gpu'], ensure_ascii=False, indent=2)}

Накопители:
{json.dumps(data['storage'], ensure_ascii=False, indent=2)}

Охлаждение:
{json.dumps(data['cooling'], ensure_ascii=False, indent=2)}

Сценарии использования:
{json.dumps(data['use_cases'], ensure_ascii=False, indent=2)}

ФОРМАТ ОТВЕТА:
1. Кратко уточни сценарий использования
2. Предложи сборку списком: CPU / Материнская плата / ОЗУ / Видеокарта / Накопитель / Охлаждение / БП
3. Для каждого компонента — одно предложение с обоснованием выбора
4. В конце — итоговая оценка бюджета (укладывается / не укладывается)

Отвечай только на русском языке. Используй только компоненты из списков выше.
"""

def ask_agent(query: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": build_system_prompt(compatibility)
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )
    return response.choices[0].message.content