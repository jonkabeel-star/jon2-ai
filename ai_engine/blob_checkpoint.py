"""Fetch an approved Jon2 checkpoint from private Vercel Blob storage.

Only known checkpoint names and SHA-256 digests are accepted. The Blob token
is read by the official Vercel SDK from the server environment and is never
returned to clients or written to logs.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

_APPROVED_CHECKPOINTS = {
    "jon2-last.pt": "edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2",
    "jon2-small.pt": "dd8cca1605050d1e72a706f42fca22269b0aa1dccf70636395b0fc2b9047a746",
}
_MAX_CHECKPOINT_BYTES = 20 * 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _download_private_blob(pathname: str, destination: Path) -> None:
    from vercel import blob

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix="jon2-checkpoint-", suffix=".tmp", dir=str(destination.parent)
    )
    temporary = Path(temporary_name)
    total = 0
    try:
        with os.fdopen(fd, "wb") as output:
            async with blob.stream_blob(pathname, access="private") as download:
                async for chunk in download:
                    total += len(chunk)
                    if total > _MAX_CHECKPOINT_BYTES:
                        raise RuntimeError("حجم ملف الأوزان تجاوز الحد المسموح.")
                    output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if total == 0:
            raise RuntimeError("ملف الأوزان المسترجع فارغ.")
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


async def ensure_private_checkpoint_async() -> Path:
    """Return a verified local checkpoint using async Blob I/O."""

    pathname = os.getenv("JON2_CHECKPOINT_BLOB", "jon2-last.pt").strip()
    expected_hash = _APPROVED_CHECKPOINTS.get(pathname)
    if expected_hash is None:
        raise RuntimeError("اسم ملف الأوزان غير معتمد في إعدادات Jon2.")

    if not os.getenv("BLOB_READ_WRITE_TOKEN"):
        raise RuntimeError("اتصال التخزين الخاص غير مهيأ على الخادم.")

    destination = Path(
        os.getenv("JON2_CHECKPOINT_CACHE", "/tmp/jon2-checkpoints")
    ) / pathname

    if destination.is_file() and _sha256_file(destination) == expected_hash:
        return destination

    destination.unlink(missing_ok=True)
    await _download_private_blob(pathname, destination)

    actual_hash = _sha256_file(destination)
    if actual_hash != expected_hash:
        destination.unlink(missing_ok=True)
        raise RuntimeError("فشل التحقق من سلامة ملف أوزان Jon2 (SHA-256).")
    return destination


def ensure_private_checkpoint() -> Path:
    """Synchronous adapter for worker-thread callers outside an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(ensure_private_checkpoint_async())
    raise RuntimeError(
        "A running event loop is active; use ensure_private_checkpoint_async()."
    )
