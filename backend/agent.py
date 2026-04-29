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

Получив запрос пользователя, выбери подходящие компоненты и верни ответ СТРОГО в два блока:

## БЛОК 1: JSON (обязательно между тегами <json> и </json>)
Верни выбранные компоненты в формате:
<json>
{{
  "scenario": "описание сценария",
  "budget": 50000,
  "components": [
    {{"name": "CPU", "model": "название модели", "price": 12000}},
    {{"name": "Материнская плата", "model": "название модели", "price": 8000}},
    {{"name": "Видеокарта", "model": "название или встроенная", "price": 0}},
    {{"name": "ОЗУ", "model": "название модели", "price": 5000}},
    {{"name": "Накопитель", "model": "название модели", "price": 4000}},
    {{"name": "Блок питания", "model": "мощность и модель", "price": 3000}}
  ]
}}
</json>

## БЛОК 2: Текстовое описание
После JSON напиши раздел "Особенности сборки" — обоснование выбора компонентов,
совместимость, рекомендации. Этот текст будет показан пользователю.

## Правила выбора:
- Процессор и материнская плата — одинаковый сокет
- Тип ОЗУ (DDR4/DDR5) совпадает с поддержкой материнской платы
- Мощность БП не ниже рекомендованной для видеокарты
- Цены реалистичные для DNS/Ситилинк/М.Видео

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
    """Вытаскиваем бюджет из запроса пользователя"""
    patterns = [
        r'(\d[\d\s]*)\s*(?:тыс(?:яч)?\.?\s*руб|тр|к\s*руб|000\s*руб)',
        r'бюджет[^\d]*(\d[\d\s]*)',
        r'за\s*(\d[\d\s]*)',
        r'(\d{4,6})\s*(?:р|руб|₽)',
        r'(\d+)\s*тыс',
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

    # Извлекаем JSON из ответа
    json_match = re.search(r'<json>(.*?)</json>', raw, re.DOTALL)
    description = re.sub(r'<json>.*?</json>', '', raw, flags=re.DOTALL).strip()

    if not json_match:
        return raw  # fallback если модель не вернула JSON

    try:
        data = json.loads(json_match.group(1).strip())
    except json.JSONDecodeError:
        return raw

    components = data.get("components", [])
    
    # ВОТ ТУТ PYTHON СЧИТАЕТ СУММУ — не доверяем модели
    total = sum(c.get("price", 0) for c in components)
    budget = budget or data.get("budget", 0)
    # Формируем красивый ответ
    rows = ""
    for c in components:
        rows += f"<tr><td>{c['name']}</td><td>{c['model']}</td><td>{c['price']:,}</td></tr>".replace(",", " ")

    status = "✅ укладывается в бюджет" if budget == 0 or total <= budget else "⚠️ превышает бюджет"
    status_class = "ok" if "✅" in status else "warn"

    result = f"""
<div class="build-result">
  <h3>Рекомендуемая сборка</h3>
  <table>
    <thead><tr><th>Компонент</th><th>Выбранная модель</th><th>Цена (₽)</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="total {status_class}">Итоговая цена: <strong>{total:,} ₽</strong> {status}</p>
  <h3>Особенности сборки</h3>
  <div class="description">{description}</div>
</div>
""".replace(",", " ")

    return result
