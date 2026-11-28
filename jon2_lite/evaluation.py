"""Deterministic evaluation helpers for Jon2 Lite.

The evaluator scores observable contract behavior; it is not a measure of
general intelligence, factual knowledge, or human-level reasoning.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EvaluationResult:
    passed: bool
    score: float
    checks: dict[str, bool]
    failures: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    prompt: str
    expected_intent: str | None = None
    required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    must_abstain: bool = False


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).lower()
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    }))
    return " ".join(value.split())


def _contains(text: str, term: str) -> bool:
    return _normalize(term) in _normalize(text)


def _context_conflicts(facts: Sequence[dict]) -> bool:
    """Detect conflicting duplicate keys if a caller supplies an unmerged set."""
    values: dict[str, set[str]] = {}
    for fact in facts:
        key = _normalize(fact.get("fact_key", ""))
        value = _normalize(fact.get("fact_value", ""))
        if key and value:
            values.setdefault(key, set()).add(value)
    return any(len(items) > 1 for items in values.values())


def _context_alignment(reply, facts: Sequence[dict], history: Sequence[dict]) -> bool:
    if reply.intent == "memory_facts":
        expected = [str(item.get("fact_value", "")).strip() for item in facts]
        expected = [value for value in expected if value]
        return all(_contains(reply.text, value) for value in expected)
    if reply.intent == "memory_history":
        expected = [
            str(item.get("content", "")).strip()
            for item in history if item.get("role") == "user"
        ][-5:]
        expected = [value for value in expected if value]
        return all(_contains(reply.text, value) for value in expected)
    if reply.intent == "step_by_step_plan":
        # Only check context claims when a recognizable goal was explicitly
        # provided. Do not invent a goal from unrelated conversation text.
        candidates = []
        for fact in facts:
            key = _normalize(fact.get("fact_key", ""))
            if any(word in key for word in ("هدف", "مجال", "تعلم", "اهتمام")):
                value = str(fact.get("fact_value", "")).strip()
                if value:
                    candidates.append(value)
        for item in history:
            if item.get("role") != "user":
                continue
            message = str(item.get("content", "")).strip()
            normalized = _normalize(message)
            if any(term in normalized for term in ("اريد تعلم", "عايز اتعلم", "هدفي", "عايز ابدا")):
                candidates.append(message)
        return not candidates or any(_contains(reply.text, value) for value in candidates)
    return True


def evaluate_reply(
    prompt: str,
    reply,
    *,
    expected_intent: str | None = None,
    required_terms: Iterable[str] = (),
    forbidden_terms: Iterable[str] = (),
    must_abstain: bool = False,
    facts: Sequence[dict] = (),
    history: Sequence[dict] = (),
) -> EvaluationResult:
    """Evaluate a reply against explicit, deterministic acceptance criteria."""
    checks = {
        "intent": expected_intent is None or reply.intent == expected_intent,
        "required_terms": all(_contains(reply.text, term) for term in required_terms),
        "forbidden_terms": not any(_contains(reply.text, term) for term in forbidden_terms),
        "abstention": not must_abstain or (
            reply.intent in {"unsupported", "unsupported_question", "clarification_needed"}
            and not reply.model_used
        ),
        "no_unverified_model_claim": not (
            reply.intent in {"unsupported", "unsupported_question", "clarification_needed"}
            and reply.model_used
        ),
        "context_consistency": not _context_conflicts(facts) and _context_alignment(reply, facts, history),
    }
    failures = tuple(name for name, passed in checks.items() if not passed)
    score = round(100 * sum(checks.values()) / len(checks), 2)
    return EvaluationResult(not failures, score, checks, failures)


def evaluate_batch(cases: Sequence[EvaluationCase], responder) -> dict:
    """Run a reproducible case suite against a callable such as brain.respond."""
    results = []
    for case in cases:
        reply = responder(case.prompt)
        result = evaluate_reply(
            case.prompt,
            reply,
            expected_intent=case.expected_intent,
            required_terms=case.required_terms,
            forbidden_terms=case.forbidden_terms,
            must_abstain=case.must_abstain,
        )
        results.append({"name": case.name, "result": result})
    passed = sum(item["result"].passed for item in results)
    total = len(results)
    return {
        "passed": passed,
        "total": total,
        "score": round(100 * passed / total, 2) if total else 100.0,
        "results": tuple(results),
    }
