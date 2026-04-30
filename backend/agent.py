import os
import json
import re
import urllib.parse
import concurrent.futures
import time
from gigachat import GigaChat
from ddgs import DDGS

def safe_ddgs_text(query, max_results=10, retries=2):
    for attempt in range(retries):
        try:
            return DDGS().text(query, region='ru-ru', max_results=max_results, timelimit=5)  # timelimit если поддерживается
        except Exception as e:
            print(f"DEBUG: попытка {attempt+1} не удалась: {e}", flush=True)
            time.sleep(2)
    return []
# ──────────────────────────────────────────────
# ЗАГРУЗКА ДАННЫХ
# ──────────────────────────────────────────────
def load_compatibility():
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "compatibility.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Если файла нет, возвращаем пустой словарь для защиты от ошибок
        return {}


compatibility = load_compatibility()


# ──────────────────────────────────────────────
# БЛОК 1: ПРОМПТ С РАССУЖДЕНИЯМИ
# ──────────────────────────────────────────────
def build_system_prompt(data: dict) -> str:
    return f"""Ты – ИИ-ассистент по подбору комплектующих для ПК.

Твоя задача — подобрать актуальное и совместимое железо.
Отвечай ТОЛЬКО на вопросы о ПК и железе. Если тема другая, пиши: "Извините, я специализируюсь только на компьютерах."
ВАЖНО: Используй ТОЛЬКО реальные модели комплектующих, которые действительно продаются в российских магазинах (DNS, Ситилинк).
Не придумывай названия. Если сомневаешься, бери самые популярные модели, например:
- Процессоры: Intel Core i5-12400F, i5-13400F, AMD Ryzen 5 5600, Ryzen 7 5700X.
- Видеокарты: GeForce RTX 3060 12GB, Radeon RX 6700 XT, GeForce RTX 4060.
- Охлаждение: DeepCool AK400, ID-COOLING SE-224-XT, Cooler Master Hyper 212.
- Блоки питания: DeepCool PK600D, Cougar STX 650W, Zalman Gigamax 650W.
Это поможет избежать выдуманных моделей.
Твой ответ должен состоять из ТРЕХ блоков строго в таком порядке:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 1 — РАССУЖДЕНИЕ (между тегами <thought> и </thought>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ОБЯЗАТЕЛЬНО напиши цепочку рассуждений:
- Какой сценарий использования и бюджет?
- Процессор и его сокет?
- Подходящая материнская плата (чипсет и сокет)?
- Тип RAM (DDR4 или DDR5), поддерживаемый платой?
- Какая видеокарта нужна и сколько ватт БП она требует?
- Конкретная модель БП (обязательно с указанием ватт, например "DeepCool PK600D 600W").

<thought>
(твои рассуждения)
</thought>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 2 — JSON-СБОРКА (теги <json> и </json>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Верни два варианта сборки: "main" (оптимальная) и "budget_build" (дешевле).
Цены ставь 0 (мы найдем их сами в интернете). Поле "model" у БП должно содержать название МОДЕЛИ, а не просто ватты!

<json>
{{
  "scenario": "краткое описание",
  "main":[
    {{"name": "CPU", "model": "Intel Core i5-12400F", "price": 0}},
    {{"name": "Материнская плата", "model": "Gigabyte B660M DS3H", "price": 0}},
    {{"name": "Видеокарта", "model": "Palit GeForce RTX 4060 Dual", "price": 0}},
    {{"name": "ОЗУ", "model": "ADATA XPG GAMMIX D20 16GB", "price": 0}},
    {{"name": "Накопитель", "model": "Kingston NV2 1TB", "price": 0}},
    {{"name": "Охлаждение", "model": "ID-COOLING SE-214-XT", "price": 0}},
    {{"name": "Блок питания", "model": "DeepCool PK550D 550W", "price": 0}}
  ],
  "budget_build":[
    {{"name": "CPU", "model": "Intel Core i3-12100F", "price": 0}},
    {{"name": "Материнская плата", "model": "MSI PRO H610M-E DDR4", "price": 0}},
    {{"name": "Видеокарта", "model": "KFA2 GeForce GTX 1650", "price": 0}},
    {{"name": "ОЗУ", "model": "Patriot Signature Line 16GB", "price": 0}},
    {{"name": "Накопитель", "model": "ADATA Legend 700 500GB", "price": 0}},
    {{"name": "Охлаждение", "model": "DeepCool GAMMAXX 300", "price": 0}},
    {{"name": "Блок питания", "model": "DeepCool PF450 450W", "price": 0}}
  ]
}}
</json>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
БЛОК 3 — ТЕКСТ (markdown)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Опиши, чем отличаются эти два варианта и дай рекомендации по апгрейду.

## Данные совместимости:
Сокеты: {json.dumps(data.get('sockets', {}), ensure_ascii=False)}
Материнские платы: {json.dumps(data.get('motherboards', {}), ensure_ascii=False)}
Видеокарты: {json.dumps(data.get('gpu', {}), ensure_ascii=False)}
"""


def fetch_real_price(model_name: str) -> int:
    try:
        # Первый запрос: ищем на трёх целевых сайтах
        search_query = f"site:dns-shop.ru OR site:citilink.ru OR site:market.yandex.ru {model_name}"
        print(f"DEBUG: ищу цену для {model_name}", flush=True)
        results = DDGS().text(search_query, region='ru-ru', max_results=10)
        prices = []
        for r in results:
            text = (r.get('body', '') + " " + r.get('title', '')).lower()
            print(f"DEBUG: сниппет: {text[:130]}...", flush=True)

            # Этап 1: числа рядом с символом рубля
            matches = re.findall(
                r'(?<!\d)(\d[\d\s]{0,7})\s*(?:руб|₽|р\.|rub)',
                text, re.IGNORECASE
            )
            for m in matches:
                clean = m.replace(' ', '')
                val = int(clean)
                if 1500 <= val <= 200000:
                    prices.append(val)
                    print(f"DEBUG: найдена цена (знак рубля): {val}", flush=True)

            # Этап 2: числа без символа рубля, но рядом с "цена" / "стоимость"
            if not matches:  # если не нашли со знаком, пробуем альтернативу
                alt_matches = re.findall(
                    r'(?:цена|стоимость)\D{0,10}?(\d[\d\s]{0,7})\b',
                    text, re.IGNORECASE
                )
                for m in alt_matches:
                    clean = m.replace(' ', '')
                    val = int(clean)
                    if 1500 <= val <= 200000:
                        prices.append(val)
                        print(f"DEBUG: найдена цена (контекст): {val}", flush=True)

        # Фильтр выбросов
        if prices:
            prices_sorted = sorted(prices)
            median = prices_sorted[len(prices_sorted)//2]
            filtered = [p for p in prices if 0.5 * median < p < 1.5 * median]
            if filtered:
                avg = sum(filtered) // len(filtered)
            else:
                avg = sum(prices) // len(prices)
            print(f"DEBUG: итоговая цена: {avg}", flush=True)
            return avg
            
        # Fallback: если на целевых сайтах ничего нет, ищем по всему интернету
        print("DEBUG: fallback – поиск по всему интернету", flush=True)
        results2 = DDGS().text(f"{model_name} цена руб", region='ru-ru', max_results=8)
        for r in results2:
            text = (r.get('body', '') + " " + r.get('title', '')).lower()
            print(f"DEBUG: fallback сниппет: {text[:130]}...", flush=True)
            # только со знаком рубля, чтобы не собирать мусор
            matches = re.findall(
                r'(?<!\d)(\d[\d\s]{0,7})\s*(?:руб|₽|р\.|rub)',
                text, re.IGNORECASE
            )
            for m in matches:
                clean = m.replace(' ', '')
                val = int(clean)
                if 1500 <= val <= 200000:
                    prices.append(val)
                    print(f"DEBUG: fallback цена: {val}", flush=True)
        if prices:
            avg = sum(prices) // len(prices)
            print(f"DEBUG: fallback итоговая цена: {avg}", flush=True)
            return avg
        else:
            print(f"DEBUG: цена не найдена", flush=True)
    except Exception as e:
        print(f"DEBUG: ошибка при поиске: {e}", flush=True)
    return 0


def update_prices(build_list: list):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_comp = {executor.submit(fetch_real_price, c['model']): c for c in build_list if isinstance(c, dict)}
        for future in concurrent.futures.as_completed(future_to_comp):
            comp = future_to_comp[future]
            try:
                comp['price'] = future.result()
            except Exception:
                comp['price'] = 0

# ──────────────────────────────────────────────
# БЛОК 3: ПРОВЕРКА СОВМЕСТИМОСТИ
# ──────────────────────────────────────────────
def validate_build(components: list, comp_data: dict) -> list[str]:
    warnings = []
    cpu_name, mb_name, ram_name, gpu_name, psu_model = None, None, None, None, None

    for c in components:
        name, model = c.get("name", "").lower(), c.get("model", "")
        if "cpu" in name or "процессор" in name:
            cpu_name = model
        elif "материнская" in name or "плата" in name:
            mb_name = model
        elif "озу" in name or "память" in name or "ram" in name:
            ram_name = model
        elif "видеокарта" in name or "gpu" in name:
            gpu_name = model
        elif "блок питания" in name or "бп" in name or "psu" in name:
            psu_model = model

    # Проверка сокета
    if cpu_name and mb_name:
        mb_info = comp_data.get("motherboards", {}).get(mb_name)
        if mb_info:
            mb_socket = mb_info.get("socket")
            cpu_socket = next((sock for sock, cpus in comp_data.get("sockets", {}).items() if cpu_name in cpus), None)
            if cpu_socket and mb_socket and cpu_socket != mb_socket:
                warnings.append(
                    f"⚠️ **Несовместимость:** {cpu_name} ({cpu_socket}) не подходит к {mb_name} ({mb_socket})")

    # Проверка типа ОЗУ (DDR4/DDR5)
    if mb_name and ram_name:
        mb_info = comp_data.get("motherboards", {}).get(mb_name)
        if mb_info:
            mb_ram_type = mb_info.get("ram_type", "")
            if mb_ram_type and mb_ram_type not in ram_name:
                warnings.append(f"⚠️ **Память:** {ram_name} не подходит к плате {mb_name} (нужна {mb_ram_type})")

    # Проверка мощности Блока Питания
    if gpu_name and psu_model:
        # ИСПРАВЛЕННЫЙ БАГ: ругаемся, только если написано просто "500W" или "450 Вт" без названия модели
        if re.match(r'^\d+\s*[WВв][Tт]?$', psu_model.strip(), re.IGNORECASE):
            warnings.append(f"⚠️ **Баг ИИ:** модель БП указана некорректно ('{psu_model}').")
        else:
            psu_watt_match = re.search(r'(\d{3,4})\s*[WВв]', psu_model)
            if psu_watt_match:
                psu_w = int(psu_watt_match.group(1))
                for tier in comp_data.get("gpu", {}).values():
                    if isinstance(tier, dict):
                        for gpu, specs in tier.items():
                            if gpu.lower() in gpu_name.lower():
                                rec_psu = specs.get("recommended_psu_w", 0)
                                if rec_psu and psu_w < rec_psu:
                                    warnings.append(
                                        f"⚠️ **Слабый БП:** для {gpu_name} нужно минимум {rec_psu}W, а выбран {psu_w}W")
    return warnings


# ──────────────────────────────────────────────
# БЛОК 4: ВСПОМОГАТЕЛЬНЫЕ И ГЛАВНАЯ ФУНКЦИЯ
# ──────────────────────────────────────────────
def extract_budget(query: str) -> int:
    for pattern in [r'(\d+)\s*тыс', r'(\d[\d\s]*)\s*(?:тыс(?:яч)?\.?\s*руб|тр|к\s*руб)', r'бюджет[^\d]*(\d[\d\s]*)',
                    r'за\s*(\d[\d\s]*)', r'(\d{4,6})\s*(?:р|руб|₽)']:
        match = re.search(pattern, query.lower())
        if match:
            num = int(match.group(1).replace(' ', ''))
            return num * 1000 if num < 1000 else num
    return 0


def get_api_key():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "r") as f:
        for line in f:
            if line.strip().startswith("GIGACHAT_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def build_table(components: list) -> str:
    rows = ""
    for c in components:
        name, model, price = c.get('name', 'Компонент'), c.get('model', 'Неизвестно'), c.get('price', 0)
        link = f"https://market.yandex.ru/search?text={urllib.parse.quote(model)}"
        model_linked = f"[{model}]({link})"

        # ИСПРАВЛЕННЫЙ БАГ С ЗАПЯТЫМИ: Форматируем цену пробелами аккуратно
        price_str = f"~{price:,}".replace(",", " ") if price > 0 else "Уточняйте в магазине"
        rows += f"| {name} | {model_linked} | {price_str} |\n"

    return f"\n| Компонент | Выбранная модель | Примерная цена (₽) |\n|-----------|:----------------|-------------------:|\n{rows}\n"


def ask_agent(query: str) -> str:
    print("DEBUG: ask_agent called", flush=True)
    api_key = get_api_key()
    print("DEBUG: api_key получен" if api_key else "DEBUG: api_key НЕ НАЙДЕН!", flush=True)
    budget = extract_budget(query)
    print(f"DEBUG: бюджет = {budget}", flush=True)

    print("DEBUG: перед созданием GigaChat", flush=True)
    with GigaChat(credentials=api_key, verify_ssl_certs=False, temperature=0.3) as giga:
        print("DEBUG: GigaChat создан, отправляю запрос...", flush=True)
        response = giga.chat({
            "messages": [
                {"role": "system", "content": build_system_prompt(compatibility)},
                {"role": "user", "content": query}
            ]
        })
        print("DEBUG: ответ от GigaChat получен", flush=True)
        raw = response.choices[0].message.content

    print("DEBUG: парсинг ответа...", flush=True)

    thought_match = re.search(r'<thought>(.*?)</thought>', raw, re.DOTALL)
    json_match = re.search(r'<json>(.*?)</json>', raw, re.DOTALL)

    after_json = re.sub(r'<thought>.*?</thought>', '', raw, flags=re.DOTALL)
    after_json = re.sub(r'<json>.*?</json>', '', after_json, flags=re.DOTALL).strip()

    if not json_match:
        return raw

    try:
        data = json.loads(json_match.group(1).strip())
    except json.JSONDecodeError:
        return raw

    main_build = data.get("main", [])

    # Пытаемся получить бюджетную сборку
    budget_build = data.get("budget_build", [])
    if not isinstance(budget_build, list):
        fallback_budget = data.get("budget")
        budget_build = fallback_budget if isinstance(fallback_budget, list) else []

    # Запускаем парсер цен в интернете
    update_prices(main_build)
    update_prices(budget_build)

    # Считаем итоговую цену сборок (складываем цены всех деталей)
    main_total = sum(c.get("price", 0) for c in main_build if isinstance(c, dict))
    budget_total = sum(c.get("price", 0) for c in budget_build if isinstance(c, dict))

    # Функция проверки: влезли ли мы в бюджет пользователя
    def status(total):
        if budget == 0 or total <= budget:
            return "✅ укладывается в бюджет"
        return "⚠️ превышает бюджет"

    # Проверяем сборки нашим Python-кодом на совместимость
    main_warnings = validate_build(main_build, compatibility)
    budget_warnings = validate_build(budget_build, compatibility)

    def format_warnings(ws):
        if not ws:
            return ""
        return "\n" + "\n".join(ws) + "\n"

    # Извлекаем рассуждения ИИ, чтобы показать их пользователю
    thought_text = thought_match.group(1).strip() if thought_match else ""

    # Делаем цены красивыми (15000 -> 15 000)
    main_total_str = f"{main_total:,}".replace(",", " ")
    budget_total_str = f"{budget_total:,}".replace(",", " ")

    # Собираем финальный текст ответа
    result = f"""### 🛠 Рассуждения ИИ
{thought_text}

---

### 🔥 Оптимальная сборка
{build_table(main_build)}
Итоговая цена: {main_total_str} ₽ {status(main_total)}
{format_warnings(main_warnings)}

---

### 💰 Бюджетный вариант
{build_table(budget_build)}
Итоговая цена: {budget_total_str} ₽ {status(budget_total)}
{format_warnings(budget_warnings)}

---

{after_json}
"""
    return result
