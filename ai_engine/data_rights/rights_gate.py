"""Strict source-rights gate for Jon2 Arabic training corpora.

A dataset is not approved merely because a repository is public or its card
says "open". Every source needs provenance and an explicit training grant.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse

BLOCKED_LICENSES = {"cc-by-sa-4.0", "cc-by-sa-3.0", "cc-by-sa-2.0", "unknown", "none", ""}
BLOCKED_SOURCE_MARKERS = {"wikipedia", "wikimedia"}
ALLOWED_LICENSES = {"cc0-1.0", "public-domain", "custom-written-permission"}

def validate_source(source: dict) -> list[str]:
    errors = []
    if not isinstance(source, dict):
        return ["source record must be an object"]
    required = ("dataset_id", "version_or_commit", "license", "training_permission",
                "rights_evidence_url", "provenance_url", "source_domains",
                "content_hash_sha256", "human_approved")
    for key in required:
        if key not in source:
            errors.append(f"missing {key}")
    if errors:
        return errors
    license_id = str(source["license"]).strip().lower()
    if license_id in BLOCKED_LICENSES:
        errors.append(f"blocked or missing license: {license_id or 'empty'}")
    elif license_id not in ALLOWED_LICENSES:
        errors.append(f"license not on Jon2 allowlist: {license_id}")
    if source["training_permission"] is not True:
        errors.append("explicit permission for model training is required")
    if source["human_approved"] is not True:
        errors.append("human approval is required")
    for field in ("rights_evidence_url", "provenance_url"):
        value = source[field]
        parsed = urlparse(value) if isinstance(value, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{field} must be an HTTPS evidence URL")
    domains = source["source_domains"]
    if not isinstance(domains, list) or not domains or not all(isinstance(x, str) and x.strip() for x in domains):
        errors.append("source_domains must be a non-empty list")
    elif any(any(marker in d.lower() for marker in BLOCKED_SOURCE_MARKERS) for d in domains):
        errors.append("Wikipedia/Wikimedia-derived sources are blocked by Jon2 policy")
    digest = source["content_hash_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        errors.append("content_hash_sha256 must be lowercase SHA-256")
    if not isinstance(source["dataset_id"], str) or not source["dataset_id"].strip():
        errors.append("dataset_id must be non-empty")
    if not isinstance(source["version_or_commit"], str) or not source["version_or_commit"].strip():
        errors.append("version_or_commit must be pinned")
    return errors

def load_approved_sources(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported rights manifest schema")
    policy = data.get("policy", {})
    if policy.get("wikipedia") != "blocked" or policy.get("cc_by_sa") != "blocked":
        raise ValueError("Jon2 non-negotiable source exclusions were weakened")
    sources = data.get("approved_sources")
    if not isinstance(sources, list):
        raise ValueError("approved_sources must be a list")
    errors = []
    for index, source in enumerate(sources):
        for error in validate_source(source):
            errors.append(f"source[{index}]: {error}")
    if errors:
        raise ValueError("Rights review failed:\n- " + "\n- ".join(errors))
    return sources
