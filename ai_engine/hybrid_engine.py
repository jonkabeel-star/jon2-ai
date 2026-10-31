"""Jon2 AI hybrid runtime: a quantized open model behind a project-owned Python layer.

The base model is an Apache-2.0 Qwen2.5 0.5B Instruct GGUF quantization.
Jon2 owns the Arabic system behavior, conversation handling, API contract, and
future memory/tools/training layers. This is a starter runtime, not a claim that
the small base model is a frontier-scale or independently trained Jon2 model.
"""
from __future__ import annotations

import os
import threading
from typing import Any

from llama_cpp import Llama


MODEL_REPO = os.getenv(
    "JON2_MODEL_REPO",
    "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
)
MODEL_FILE = os.getenv(
    "JON2_MODEL_FILE",
    "*q4_k_m.gguf",
)
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_CHARS = 6000

SYSTEM_PROMPT = (
    "أنت Jon2 AI، مساعد عربي ذكي وواضح. أجب بلغة المستخدم، "
    "واجعل العربية طبيعية ومفهومة عند استخدامها. أجب مباشرة وبمعلومات دقيقة. "
    "إذا لم تكن متأكدًا فقل ذلك بوضوح ولا تخترع أسماء أو أحداثًا أو مصادر. "
    "لا تدّعِ أنك نفذت إجراءً لم تنفذه. نظّم الإجابة عند الحاجة."
)


class Jon2HybridEngine:
    """Lazy-loaded local GGUF model with a Jon2-controlled conversation layer."""

    def __init__(self) -> None:
        self.model: Llama | None = None
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()
        self.n_ctx = int(os.getenv("JON2_CONTEXT_SIZE", "4096"))
        self.n_threads = int(
            os.getenv("JON2_CPU_THREADS", str(max(1, min(os.cpu_count() or 2, 4))))
        )
        self.max_tokens = int(os.getenv("JON2_MAX_NEW_TOKENS", "300"))

    @property
    def ready(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        if self.ready:
            return
        with self._load_lock:
            if self.ready:
                return
            try:
                self.model = Llama.from_pretrained(
                    repo_id=MODEL_REPO,
                    filename=MODEL_FILE,
                    n_ctx=self.n_ctx,
                    n_threads=self.n_threads,
                    n_batch=128,
                    verbose=False,
                )
            except Exception as exc:
                self.model = None
                raise RuntimeError(
                    "تعذر تحميل نموذج Jon2 الأساسي. تحقق من اتصال الإنترنت "
                    "ومساحة التخزين وتثبيت llama-cpp-python."
                ) from exc

    @staticmethod
    def _clean_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        if not isinstance(history, list):
            return cleaned

        for item in history[-MAX_HISTORY_MESSAGES:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str):
                continue
            content = content.strip()
            if content:
                cleaned.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
        return cleaned

    def reply(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("اكتب رسالتك أولًا.")
        message = message.strip()
        if len(message) > MAX_MESSAGE_CHARS:
            raise ValueError("الرسالة طويلة جدًا. اختصرها ثم حاول مرة أخرى.")

        self.load()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self._clean_history(history))
        messages.append({"role": "user", "content": message})

        try:
            with self._generation_lock:
                result = self.model.create_chat_completion(
                    messages=messages,
                    max_tokens=max(32, min(self.max_tokens, 512)),
                    temperature=0.35,
                    top_p=0.85,
                    repeat_penalty=1.12,
                )
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("النموذج لم يُرجع إجابة.")
            return answer.strip()
        except Exception as exc:
            raise RuntimeError("حدث خطأ أثناء توليد إجابة Jon2 AI.") from exc


engine = Jon2HybridEngine()
