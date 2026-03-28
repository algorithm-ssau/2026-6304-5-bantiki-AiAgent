# PC Builder Agent

AI-агент для подбора комплектующих ПК под задачи и бюджет.

---

## Что делает

Пользователь описывает задачу и бюджет — агент подбирает совместимые комплектующие и объясняет выбор.

**Основные функции:**
- Подбор комплектующих под конкретные задачи
- Проверка совместимости всех компонентов
- Учет бюджета пользователя
- Детальное объяснение выбора каждой детали

---

## Стек технологий

| Технология | Назначение |
|-----------|-----------|
| Python + FastAPI | Backend API |
| React + Vite | Frontend интерфейс |
| Groq (llama-3.3-70b) | LLM для генерации рекомендаций |

---

## Запуск

### Требования
- Python 3.11+
- Node.js 18+
- API ключ Groq

### Backend

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

### Frontend

cd frontend
npm install
npm run dev

---

## Команда

| Фото | Имя | Должность |
|------|-----|----------|
| 📷 | Ирина Сергеевна | Team Lead |
| 📷 | Настя | Backend Developer |
| 📷 | Даша | Frontend Developer |
| 📷 | Настя | ML Engineer |
| 📷 | Даша | QA Engineer |
| 📷 | Маша | QA Engineer |
