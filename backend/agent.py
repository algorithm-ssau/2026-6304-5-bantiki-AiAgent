import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_agent(query: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — AI-агент по подбору комплектующих для ПК. "
                    "Пользователь описывает задачу и бюджет, ты подбираешь "
                    "конкретные совместимые комплектующие с объяснением выбора. "
                    "Отвечай на русском языке."
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )
<<<<<<< HEAD
    return response.choices[0].message.content
=======
    return response.choices[0].message.content
>>>>>>> 898178117a8ceefff44ef60c1f37bb4059feca80
