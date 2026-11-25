"""Vercel entrypoint for the existing Jon2 FastAPI application.

This module only exposes the original application; it does not create a
second model, bypass release gates, or load checkpoint weights on Vercel.
"""
from pathlib import Path
import sys

AI_ENGINE_DIR = Path(__file__).resolve().parents[1] / "ai_engine"
sys.path.insert(0, str(AI_ENGINE_DIR))

from main import app  # noqa: E402

__all__ = ["app"]
