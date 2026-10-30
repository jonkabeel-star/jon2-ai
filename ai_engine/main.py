import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chat_engine import generate_reply, model_is_ready, load_model

app = FastAPI(
    title="Jon2 AI API",
    description="Independent Jon2 AI chat API powered by an open-source language model.",
    version="1.0.0",
)

# GitHub Pages frontend + local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jonkabeel-star.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "project": "Jon2 AI",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {
        "project": "Jon2 AI",
        "status": "online",
        "model": os.getenv("JON2_CHAT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        "model_loaded": model_is_ready(),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="اكتب رسالتك أولًا.")

    try:
        # Load lazily on the first chat request, not during deployment startup.
        load_model()
        reply = generate_reply(request.message.strip())
        if not reply:
            raise RuntimeError("The model returned an empty response.")
        return {"project": "Jon2 AI", "reply": reply}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        print(f"Jon2 AI chat error: {error}")
        raise HTTPException(
            status_code=503,
            detail="تعذر تشغيل نموذج Jon2 AI. راجع سجلات الخادم وذاكرة التشغيل.",
        )
