import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_agent(query: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Ty — AI-agent po podboru komplektuyuschikh dlya PK. Polzovatel opisyvaet zadachu i byudzhet, ty podbirаesh sovmestimye komplektuyuschie s obyasneniem vybora. Otvechay na russkom yazyke."
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )
    return response.choices[0].message.content