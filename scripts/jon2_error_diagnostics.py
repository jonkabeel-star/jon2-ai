"""Structured, data-only diagnosis for common Jon2 CI/runtime failures.

This module never executes log content and never edits repository files.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

ERROR_RULES = (
    ("syntax_error", re.compile(r"(?m)^\s*(?:SyntaxError|IndentationError|TabError):\s*(.+)$"), "راجع السطر المشار إليه وأصلح تركيب Python أو المسافات يدويًا؛ لا يُعاد تنسيق المنطق تلقائيًا.", "high"),
    ("module_not_found", re.compile(r"(?m)^ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]"), "تحقق هل الوحدة من المكتبات القياسية أم اعتماد خارجي؛ لا تضف حزمة تلقائيًا قبل مراجعة requirements وبيئة التشغيل.", "high"),
    ("import_error", re.compile(r"(?m)^ImportError: (.+)$"), "افحص اسم الاستيراد وإصدار الحزمة ومسار الوحدة؛ لا تغيّر الاعتمادات تلقائيًا.", "high"),
    ("name_error", re.compile(r"(?m)^NameError: name ['\"]([^'\"]+)['\"] is not defined"), "تحقق من نطاق الاسم والاستيرادات؛ يطبق المحرك فقط قاعدة الاستيراد القياسية المسموح بها.", "medium"),
    ("attribute_error", re.compile(r"(?m)^AttributeError: (.+)$"), "تحقق من نوع الكائن واسم الخاصية وتوافق إصدار المكتبة؛ يلزم تعديل منطقي ومراجعة بشرية.", "high"),
    ("type_error", re.compile(r"(?m)^TypeError: (.+)$"), "افحص أنواع وقيم الوسائط وتوقيع الدالة؛ لا يغيّر المحرك منطق الاستدعاء تلقائيًا.", "high"),
    ("value_error", re.compile(r"(?m)^ValueError: (.+)$"), "افحص قيمة الإدخال والقيود المتوقعة؛ أضف اختبار حالة حدية قبل أي تعديل.", "medium"),
    ("assertion_failure", re.compile(r"(?m)^AssertionError(?::\s*(.*))?$"), "قارن القيمة الفعلية والمتوقعة وحدد هل الخلل في التنفيذ أم في افتراض الاختبار؛ لا يخفف الاختبار تلقائيًا.", "high"),
    ("file_not_found", re.compile(r"(?m)^(?:FileNotFoundError|OSError): (.+)$"), "تحقق من وجود الملف ومساره النسبي وملفات CI؛ لا ينشئ ملفات بيانات أو checkpoints تلقائيًا.", "medium"),
    ("permission_error", re.compile(r"(?m)^PermissionError: (.+)$"), "راجع صلاحيات الملف وGITHUB_TOKEN وأقل الصلاحيات اللازمة؛ لا يوسع صلاحيات workflow تلقائيًا.", "high"),
    ("timeout", re.compile(r"(?mi)(?:timed out|timeout expired|CHECK TIMED OUT)"), "افحص زمن الاختبار والموارد واحتمال التعليق؛ لا يرفع حدود الوقت تلقائيًا.", "medium"),
    ("http_error", re.compile(r"(?m)^(?:HTTPError|requests\.exceptions\.(?:ConnectionError|Timeout)): (.+)$"), "تحقق من توافر الخدمة والشبكة وإعادة المحاولة وحدود المعدل؛ لا يغير endpoints أو الأسرار.", "medium"),
)

TEST_NAME = re.compile(r"(?m)^\s*(?:FAIL|ERROR):\s*([A-Za-z0-9_.:-]+)")
TRACE_LOCATION = re.compile(r'File ["\']([^"\']+\.py)["\'], line (\d+)(?:, in ([^\s]+))?')
PYTHON_LINE = re.compile(r"(?m)^\s*([A-Za-z0-9_./-]+\.py):(\d+)(?::\d+)?:\s*(?:error|warning):\s*(.+)$")


def analyze_failure_log(log_text: str) -> dict:
    """Return bounded, structured diagnoses; treat supplied logs strictly as data."""
    diagnoses = []
    seen = set()
    for category, pattern, recommendation, severity in ERROR_RULES:
        match = pattern.search(log_text)
        if not match or category in seen:
            continue
        seen.add(category)
        details = match.group(1) if match.lastindex else match.group(0).strip()
        location = TRACE_LOCATION.search(log_text)
        diagnostic = {
            "category": category,
            "severity": severity,
            "message": str(details)[:500],
            "recommendation": recommendation,
        }
        if location:
            diagnostic["file"] = PurePosixPath(location.group(1)).as_posix()[-240:]
            diagnostic["line"] = int(location.group(2))
            if location.group(3):
                diagnostic["function"] = location.group(3)[:120]
        diagnoses.append(diagnostic)

    failed_tests = list(dict.fromkeys(TEST_NAME.findall(log_text)))[:50]
    compiler = PYTHON_LINE.search(log_text)
    if compiler:
        diagnoses.append({
            "category": "python_lint_or_compile",
            "severity": "medium",
            "file": compiler.group(1)[-240:],
            "line": int(compiler.group(2)),
            "message": compiler.group(3)[:500],
            "recommendation": "افتح السطر المحدد وشغّل compileall والاختبارات ذات الصلة بعد إصلاحه.",
        })
    return {
        "diagnoses": diagnoses[:20],
        "failed_tests": failed_tests,
        "recognized_error_types": len(diagnoses),
        "log_content_executed": False,
        "automatic_repair_allowed": False,
    }
