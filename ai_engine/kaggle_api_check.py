"""Run a safe API smoke test inside a Kaggle/Colab Python notebook.

This test checks the FastAPI contract only. It does not train a model,
download weights, expose a public URL, or approve a checkpoint.
"""
import os
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

# Keep chat closed during this diagnostic run.
os.environ["JON2_CHAT_RELEASE_APPROVED"] = "false"

from fastapi.testclient import TestClient
from main import app

def main() -> int:
    print("Jon2 API smoke test")
    print("===================")

    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200, home.text
        print("[PASS] GET /")

        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        data = health.json()
        assert data.get("project") == "Jon2 AI"
        assert data.get("release_approved") is False
        assert data.get("chat_ready") is False
        print("[PASS] GET /api/health")
        print("       checkpoint_configured:", data.get("checkpoint_configured"))
        print("       model_loaded:", data.get("model_loaded"))
        print("       chat_ready:", data.get("chat_ready"))

        chat = client.post("/api/chat", json={"message": "مرحبا"})
        assert chat.status_code == 503, (
            "Chat must remain blocked until a reviewed checkpoint is approved. "
            f"Received {chat.status_code}: {chat.text}"
        )
        print("[PASS] POST /api/chat is safely blocked (HTTP 503)")

    print("\nAPI software smoke test passed.")
    print("This does NOT mean the language model is trained or ready.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
