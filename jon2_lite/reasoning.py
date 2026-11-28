"""Small, deterministic reasoning helpers for Jon2 Lite.

This module does not claim general reasoning or use a remote model. It supports
bounded arithmetic and simple, transparent task decomposition, and abstains
when intent or required information is unclear.
"""
from __future__ import annotations

import ast
import operator
import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ReasoningResult:
    intent: str
    confidence: float
    steps: tuple[str, ...]
    answer: str
    used_context: bool = False


def normalize_arabic(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).strip().lower()
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    }))
    return " ".join(value.split())


def _arithmetic(expression: str) -> int | float:
    operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos,
    }

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1_000_000_000:
                raise ValueError("number_out_of_range")
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Mult) and abs(left) * abs(right) > 1_000_000_000:
                raise ValueError("result_out_of_range")
            if isinstance(node.op, ast.Div) and right == 0:
                raise ZeroDivisionError("division_by_zero")
            return operators[type(node.op)](left, right)
        raise ValueError("unsupported_expression")

    parsed = ast.parse(expression, mode="eval")
    result = evaluate(parsed)
    if abs(result) > 1_000_000_000:
        raise ValueError("result_out_of_range")
    return result


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(round(value, 8)) if isinstance(value, float) else str(value)


def _goal_from_context(history: Sequence[dict], facts: Sequence[dict]) -> str | None:
    for fact in facts:
        key = normalize_arabic(str(fact.get("fact_key", "")))
        if any(term in key for term in ("هدف", "مجال", "تعلم", "اهتمام")):
            value = str(fact.get("fact_value", "")).strip()
            if value:
                return value
    for item in reversed(history):
        if item.get("role") != "user":
            continue
        message = str(item.get("content", "")).strip()
        normalized = normalize_arabic(message)
        if any(term in normalized for term in ("اريد تعلم", "عايز اتعلم", "هدفي", "عايز ابدا")):
            return message
    return None


def reason(text: str, language_style: str, history: Sequence[dict] = (),
           facts: Sequence[dict] = ()) -> ReasoningResult | None:
    """Return a bounded result only for supported, sufficiently clear tasks."""
    query = normalize_arabic(text)

    # Arithmetic is accepted only when the entire extracted expression is safe.
    candidate = re.sub(r"^(احسب|احسبلي|ناتج|كام|كم يساوي)\s*", "", query)
    candidate = candidate.rstrip(" ؟?")
    if re.fullmatch(r"[0-9\s+\\-*/()%]+", candidate) and re.search(r"[+*/%]", candidate):
        try:
            value = _arithmetic(candidate)
        except (SyntaxError, ValueError, ZeroDivisionError):
            return ReasoningResult("uncertain", 0.0, (), "", False)
        prefix = "الناتج هو" if language_style == "msa" else "الناتج هو"
        return ReasoningResult("arithmetic", 0.99, (
            "تحديد الأرقام والعمليات في التعبير.",
            "تنفيذ العمليات وفق أولوية الأقواس والضرب والقسمة ثم الجمع والطرح.",
            f"التحقق من الناتج: {_format_number(value)}.",
        ), f"{prefix} {_format_number(value)}.", False)

    asks_for_steps = any(term in query for term in (
        "كيف ابدا", "ازاي ابدا", "كيف اتعلم", "ازاي اتعلم",
        "كيف انظم", "ازاي انظم", "ما الخطوات", "ايه الخطوات",
        "كيف احل", "ازاي احل", "ساعدني في التخطيط", "عايز خطة",
        "اريد خطة", "اعمل خطة", "خطه",
    ))
    if asks_for_steps:
        goal = _goal_from_context(history, facts)
        tail = re.split(
            r"(?:كيف ابدا|ازاي ابدا|كيف اتعلم|ازاي اتعلم|كيف انظم|ازاي انظم|"
            r"ما الخطوات|ايه الخطوات|كيف احل|ازاي احل|عايز خطة|اريد خطة|اعمل خطة|خطه)",
            query, maxsplit=1
        )
        subject = tail[-1].strip(" ؟?،,.") if len(tail) > 1 else ""
        if not subject and goal:
            subject = goal
        if not subject:
            return ReasoningResult("clarification_needed", 0.45, (),
                "ما المهارة أو المشكلة التي تريد وضع خطوات لها؟" if language_style == "msa"
                else "عايز تحط خطوات لإيه بالظبط؟", False)
        steps = (
            f"تحديد الهدف بدقة: {subject}.",
            "تقسيم الهدف إلى مهام صغيرة يمكن إنجاز كل واحدة منها.",
            "ترتيب المهام من الأساسيات إلى الأكثر صعوبة.",
            "تحديد وقت واقعي لكل مهمة والبدء بأول مهمة.",
            "مراجعة التقدم وتعديل الخطة بناءً على ما تم إنجازه.",
        )
        lead = "يمكننا التعامل مع الهدف بهذه الخطوات:" if language_style == "msa" else "نقدر نمشي في الهدف ده بالخطوات دي:"
        return ReasoningResult("step_by_step_plan", 0.86, steps,
            lead + "\n" + "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)),
            bool(goal))

    # A vague comparison/decision is not answered without options or criteria.
    if any(term in query for term in ("انهي افضل", "ايهما افضل", "اختار ايه", "اختار انهي")):
        return ReasoningResult("clarification_needed", 0.35, (),
            "اذكر الخيارات ومعيار المقارنة، مثل السعر أو الوقت أو الجودة." if language_style == "msa"
            else "قولّي الاختيارات وهنقارن على أساس إيه: السعر ولا الوقت ولا الجودة؟", False)
    return None
