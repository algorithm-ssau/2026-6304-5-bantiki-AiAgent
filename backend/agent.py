import os
import json
import re
from gigachat import GigaChat

def load_compatibility():
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "compatibility.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

compatibility = load_compatibility()

def build_system_prompt(data: dict) -> str:
    return f"""Ты – ИИ-ассистент по подбору комплектующих для ПК.

Твой ответ должен содержать ДВА блока — строго в таком порядке:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 1 — машиночитаемый JSON (между тегами <json> и </json>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<json>
{{
  "scenario": "краткое описание сценария",
  "budget": 50000,
  "components": [
    {{"name": "CPU", "model": "Intel Core i5-13400F", "price": 12000}},
    {{"name": "Материнская плата", "model": "ASUS PRIME B660M-A", "price": 8000}},
    {{"name": "Видеокарта", "model": "RTX 3060", "price": 22000}},
    {{"name": "ОЗУ", "model": "Kingston Fury Beast 16GB DDR4-3200", "price": 5000}},
    {{"name": "Накопитель", "model": "Kingston NV2 500GB", "price": 4000}},
    {{"name": "Охлаждение", "model": "DeepCool GAMMAXX 400", "price": 1500}},
    {{"name": "Блок питания", "model": "550 Вт", "price": 4000}}
  ]
}}
</json>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 2 — текст для пользователя (markdown)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
После закрывающего тега </json> напиши следующие секции в markdown:

### Возможные варианты компонентов
Таблица со ВСЕМИ доступными вариантами для каждого компонента и диапазоном цен.
Модели в одну строку через " / ".

| Компонент | Варианты моделей | Диапазон цен (₽) |
|-----------|-----------------|-----------------|
| CPU | модель1 / модель2 | ХХХХ - ХХХХ |

### Особенности сборки
- Обоснование совместимости (сокет, тип ОЗУ)
- Почему выбраны именно эти компоненты
- Рекомендации по апгрейду

ПРАВИЛА:
- В JSON указывай РЕАЛЬНЫЕ цены на каждый компонент (DNS/Ситилинк/М.Видео)
- Процессор и мат. плата — одинаковый сокет
- Тип ОЗУ совпадает с поддержкой мат. платы
- БП не ниже рекомендованного для видеокарты

## Доступные компоненты:

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
"""

def extract_budget(query: str) -> int:
    patterns = [
        r'(\d+)\s*тыс',
        r'(\d[\d\s]*)\s*(?:тыс(?:яч)?\.?\s*руб|тр|к\s*руб)',
        r'бюджет[^\d]*(\d[\d\s]*)',
        r'за\s*(\d[\d\s]*)',
        r'(\d{4,6})\s*(?:р|руб|₽)',
    ]
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            num_str = match.group(1).replace(' ', '')
            num = int(num_str)
            if num < 1000:
                num *= 1000
            return num
    return 0

def get_api_key():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GIGACHAT_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None

def ask_agent(query: str) -> str:
    api_key = get_api_key()
    budget = extract_budget(query)

    with GigaChat(
        credentials=api_key,
        verify_ssl_certs=False,
        temperature=0.1
    ) as giga:
        response = giga.chat({
            "messages": [
                {"role": "system", "content": build_system_prompt(compatibility)},
                {"role": "user", "content": query}
            ]
        })
        raw = response.choices[0].message.content

    # Извлекаем JSON
    json_match = re.search(r'<json>(.*?)</json>', raw, re.DOTALL)
    # Текст после </json> — это markdown для пользователя
    after_json = re.sub(r'<json>.*?</json>', '', raw, flags=re.DOTALL).strip()

    if not json_match:
        return raw  # fallback

    try:
        data = json.loads(json_match.group(1).strip())
    except json.JSONDecodeError:
        return raw

    components = data.get("components", [])
    budget = budget or data.get("budget", 0)

    # Python считает итог — модель не считает
    total = sum(c.get("price", 0) for c in components)
    status = "✅ укладывается в бюджет" if budget == 0 or total <= budget else "⚠️ превышает бюджет"

    # Строим таблицу рекомендуемой сборки
    rows = ""
    for c in components:
        rows += f"| {c['name']} | {c['model']} | {c['price']:,} |\n".replace(",", " ")

    recommended_table = f"""### Рекомендуемая сборка

| Компонент | Выбранная модель | Цена (₽) |
|-----------|-----------------|----------|
{rows}
Итоговая цена: {total:,} ₽ {status}
""".replace(",", " ")

    # Итоговый ответ: варианты от модели + рекомендуемая таблица с правильной суммой
    return after_json + "\n\n" + recommended_table
