"""Phase-1 Arabic corpus coverage audit with explicit human dialect annotations.

No automatic dialect classification is attempted. A source contributes to MSA
or Egyptian counts only when its exact SHA-256 has a matching human annotation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LABELS = {"msa", "egyptian", "mixed", "other"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_annotations(path: Path) -> dict[str, dict]:
    annotations = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid annotation JSON at line {number}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Annotation line {number} must be an object.")
        name, label = item.get("file"), item.get("label")
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise ValueError(f"Annotation line {number} needs a simple file name.")
        if label not in LABELS:
            raise ValueError(f"Annotation {name} label must be one of {sorted(LABELS)}.")
        for field in ("sha256", "reviewer", "review_date"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Annotation {name} requires {field}.")
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError(f"Annotation {name} has an invalid SHA-256.")
        if name in annotations:
            raise ValueError(f"Duplicate dialect annotation for {name}.")
        annotations[name] = item
    return annotations


def build_report(data_dir: Path, annotation_file: Path) -> dict:
    root = data_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {data_dir}")
    files = sorted(p for p in root.rglob("*.txt") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No UTF-8 .txt files found in {data_dir}")
    annotations = load_annotations(annotation_file)
    counts = Counter()
    sources = []
    unannotated = []
    for path in files:
        raw = path.read_bytes()
        content = raw.decode("utf-8", errors="strict")
        name = path.relative_to(root).as_posix()
        digest = hashlib.sha256(raw).hexdigest()
        arabic_chars = len(ARABIC_RE.findall(content))
        record = {
            "file": name,
            "sha256": digest,
            "characters": len(content),
            "arabic_script_characters": arabic_chars,
            "human_dialect_label": None,
        }
        annotation = annotations.get(name)
        if annotation is None:
            unannotated.append(name)
        else:
            if annotation["sha256"] != digest:
                raise ValueError(f"Stale dialect annotation: SHA-256 changed for {name}.")
            record["human_dialect_label"] = annotation["label"]
            record["reviewer"] = annotation["reviewer"]
            record["review_date"] = annotation["review_date"]
            counts[annotation["label"]] += arabic_chars
        sources.append(record)
    unknown = sorted(set(annotations) - {item["file"] for item in sources})
    if unknown:
        raise ValueError(f"Annotations reference missing files: {unknown}")
    total_arabic = sum(item["arabic_script_characters"] for item in sources)
    return {
        "report_version": 1,
        "audit_type": "phase1_human_annotated_arabic_coverage",
        "automatic_dialect_classification": False,
        "source_count": len(sources),
        "total_characters": sum(item["characters"] for item in sources),
        "total_arabic_script_characters": total_arabic,
        "human_annotated_arabic_characters": sum(counts.values()),
        "unannotated_files": unannotated,
        "human_annotated_arabic_characters_by_label": dict(sorted(counts.items())),
        "coverage_fraction": round(sum(counts.values()) / total_arabic, 6) if total_arabic else 0.0,
        "sources": sources,
        "limitations": [
            "Arabic Unicode character counts are not token counts.",
            "Dialect labels are accepted only from the human annotation file.",
            "This report does not assess correctness, coherence, rights, privacy, or training readiness.",
            "No data is approved, modified, or sent to training by this audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit human-reviewed MSA/Egyptian coverage.")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--annotations", default="ai_engine/training_data/dialect_annotations.jsonl")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = build_report(Path(args.data), Path(args.annotations))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
