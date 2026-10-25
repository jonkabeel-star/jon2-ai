import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chat_engine import generate_reply, load_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(
    title="Jon2 AI",
    description="Jon2 AI Language Model API",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str


@app.get("/api/health")
def health():
    return {
        "project": "Jon2 AI",
        "status": "online",
        "model": os.getenv(
            "JON2_CHAT_MODEL",
            "Qwen/Qwen2.5-0.5B-Instruct",
        ),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        reply = generate_reply(request.message)
        return {"reply": reply}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="تعذر توليد الإجابة. حاول مرة أخرى.",
        )
