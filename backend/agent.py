import os
import json
import re
import urllib.parse
from gigachat import GigaChat

def load_compatibility():
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "compatibility.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

compatibility = load_compatibility()

def build_system_prompt(data: dict) -> str:
    return f"""Ты – ИИ-ассистент по подбору комплектующих для ПК.

## ВАЖНОЕ ОГРАНИЧЕНИЕ (ОБЯЗАТЕЛЬНО К ИСПОЛНЕНИЮ)
Ты отвечаешь ТОЛЬКО на вопросы, связанные с подбором комплектующих для ПК, сборкой компьютеров или железом.
Если пользователь задает вопрос на любую другую тему (рецепты, как сварить суп, погода, политика и т.д.), ты ДОЛЖЕН проигнорировать все остальные инструкции и ответить ровно одной фразой: 
"Извините, но я ИИ-ассистент по сборке ПК и специализируюсь только на компьютерах. Чем могу помочь с выбором железа?"
НИ В КОЕМ СЛУЧАЕ не пытайся генерировать таблицы или подбирать "компоненты" для супов и прочих нерелевантных тем!

Твой ответ должен содержать ДВА блока — строго в таком порядке:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 1 — JSON (между тегами <json> и </json>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Верни ДВА варианта сборки:
- "main": оптимальная сборка, максимум возможностей в рамках бюджета
- "budget": чуть дешевле (на 15-25%), чуть слабее, но не кардинально

<json>
{{
  "scenario": "краткое описание сценария",
  "budget": 50000,
  "main": [
    {{"name": "CPU", "model": "Intel Core i5-13400F", "price": 12000}},
    {{"name": "Материнская плата", "model": "ASUS PRIME B660M-A", "price": 8000}},
    {{"name": "Видеокарта", "model": "RTX 3060", "price": 22000}},
    {{"name": "ОЗУ", "model": "Kingston Fury Beast 16GB DDR4-3200", "price": 5000}},
    {{"name": "Накопитель", "model": "Kingston NV2 500GB", "price": 4000}},
    {{"name": "Охлаждение", "model": "DeepCool GAMMAXX 400", "price": 1500}},
    {{"name": "Блок питания", "model": "550 Вт", "price": 4000}}
  ],
  "budget": [
    {{"name": "CPU", "model": "Intel Core i3-12100F", "price": 8000}},
    {{"name": "Материнская плата", "model": "ASUS PRIME B660M-A", "price": 8000}},
    {{"name": "Видеокарта", "model": "GTX 1660 Super", "price": 16000}},
    {{"name": "ОЗУ", "model": "Kingston Fury Beast 8GB DDR4-3200", "price": 3000}},
    {{"name": "Накопитель", "model": "Kingston NV2 500GB", "price": 4000}},
    {{"name": "Охлаждение", "model": "be quiet! Pure Rock 2", "price": 1200}},
    {{"name": "Блок питания", "model": "450 Вт", "price": 3500}}
  ]
}}
</json>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 2 — текст для пользователя (markdown)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
После </json> напиши ТОЛЬКО:

### Особенности сборки
- Совместимость компонентов (сокет, тип ОЗУ)
- Чем отличаются два варианта и когда выбрать каждый
- Рекомендации по апгрейду

НЕ НУЖНО писать таблицы с вариантами всех компонентов — только особенности.

ПРАВИЛА:
- Процессор и мат. плата — одинаковый сокет
- Тип ОЗУ совпадает с поддержкой мат. платы
- БП не ниже рекомендованного для видеокарты
- Цены реалистичные (DNS/Ситилинк/М.Видео)
- Оба варианта должны быть совместимы

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

def build_table(components: list) -> str:
    rows = ""
    for c in components:
        name = c.get('name', 'Компонент')
        model = c.get('model', 'Неизвестно')
        price = c.get('price', 0)
        
        # 1. Формируем безопасный запрос для поиска (например, заменяем пробелы на %20)
        search_query = urllib.parse.quote(model)
        
        # 2. Генерируем 100% рабочие ссылки на агрегаторы:
        # Можно использовать Яндекс.Маркет:
        link = f"https://market.yandex.ru/search?text={search_query}"
        
        # Или e-Katalog:
        # link = f"https://www.e-katalog.ru/ek-list.php?search_={search_query}"
        
        # 3. Делаем кликабельное название
        model_linked = f"[{model}]({link})"
        
        # 4. Добавляем знак "~" (примерно) к цене, чтобы не врать пользователю
        rows += f"| {name} | {model_linked} | ~{price:,} |\n".replace(",", " ")
        
    # Меняем заголовок таблицы на "Примерная цена", так честнее
    return f"\n| Компонент | Выбранная модель | Примерная цена (₽) |\n|-----------|:----------------|-------------------:|\n{rows}\n"
    
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

    json_match = re.search(r'<json>(.*?)</json>', raw, re.DOTALL)
    after_json = re.sub(r'<json>.*?</json>', '', raw, flags=re.DOTALL).strip()

    if not json_match:
        return raw

    try:
        data = json.loads(json_match.group(1).strip())
    except json.JSONDecodeError:
        return raw

   # 1. Безопасно получаем внешний бюджет (защита от списков)
    current_budget = 0
    if isinstance(budget, list) and budget:
        try: current_budget = int(budget[0])
        except: pass
    else:
        try: current_budget = int(budget)
        except (ValueError, TypeError): pass

    # 2. Достаем основную сборку
    main_build = data.get("main", [])
    if not isinstance(main_build, list):
        main_build = []

    # 3. Разбираемся с шизофренией Гигачата (число или список?)
    raw_budget_from_llm = data.get("budget")
    budget_build = []
    
    if isinstance(raw_budget_from_llm, list):
        # Если прислал детали — сохраняем как дешевую сборку
        budget_build = raw_budget_from_llm
    elif isinstance(raw_budget_from_llm, int) or isinstance(raw_budget_from_llm, float):
        # Если прислал деньги — сохраняем их в бюджет (если своего нет)
        if current_budget == 0:
            current_budget = int(raw_budget_from_llm)

    # 4. Считаем итог с защитой от кривых данных внутри списков
    main_total = sum(c.get("price", 0) for c in main_build if isinstance(c, dict))
    budget_total = sum(c.get("price", 0) for c in budget_build if isinstance(c, dict))

    def status(total):
        if current_budget == 0 or total <= current_budget:
            return "✅ укладывается в бюджет"
        return "⚠️ превышает бюджет"

    result = f"""### 🔥 Оптимальная сборка
    

{build_table(main_build)}
Итоговая цена: {main_total} ₽ {status(main_total)}

---

### 💰 Бюджетный вариант
{build_table(budget_build)}
Итоговая цена: {budget_total} ₽ {status(budget_total)}

---

{after_json}
"""
    return result
