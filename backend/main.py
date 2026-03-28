from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent import ask_agent

app = FastAPI(title="PC Builder Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/chat")
def chat(query: str):
    answer = ask_agent(query)
    return {"answer": answer}
