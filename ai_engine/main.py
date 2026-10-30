import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chat_engine import generate_reply, model_is_ready, load_runtime

app = FastAPI(
    title="Jon2 AI API",
    description="API for the original, project-owned Jon2 language model.",
    version="1.1.0",
)

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
    message: str = Field(min_length=1, max_length=2000)


@app.get("/")
def home():
    return {
        "project": "Jon2 AI",
        "status": "api_online",
        "model": "Jon2 Original Transformer",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {
        "project": "Jon2 AI",
        "status": "online",
        "model": "Jon2 Original Transformer",
        "model_loaded": model_is_ready(),
        "checkpoint_configured": os.path.isfile(
            os.getenv(
                "JON2_CHECKPOINT",
                os.path.join(os.path.dirname(__file__), "checkpoints", "jon2-small.pt"),
            )
        ),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="اكتب رسالتك أولًا.")
    try:
        load_runtime()
        reply = generate_reply(message)
        return {"project": "Jon2 AI", "reply": reply}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        print(f"Jon2 AI chat error: {error}")
        raise HTTPException(
            status_code=503,
            detail="تعذر تشغيل نموذج Jon2 الأصلي. راجع سجلات الخادم.",
        )
