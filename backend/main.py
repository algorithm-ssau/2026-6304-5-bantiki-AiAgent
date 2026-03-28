from fastapi import FastAPI
from agent import ask_agent

app = FastAPI(title="PC Builder Agent")

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/chat")
def chat(query: str):
    answer = ask_agent(query)
    return {"answer": answer}