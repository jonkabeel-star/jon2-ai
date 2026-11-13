"""Extract and syntax-check inline JavaScript from the static Jon2 website."""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path


class InlineScriptParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.current = None
        self.parts: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attr = dict(attrs)
            self.current = [attr.get("type", ""), ""]

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.current is not None:
            self.parts.append((self.current[0], self.current[1]))
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data


def check_inline_scripts(html_path: Path) -> int:
    html = html_path.read_text(encoding="utf-8")
    config_path = html_path.parent / "jon2-config.js"
    if '<script src="jon2-config.js"></script>' not in html:
        raise AssertionError("The website must load jon2-config.js before its chat client.")
    if not config_path.is_file() or "window.JON2_API_BASE_URL" not in config_path.read_text(encoding="utf-8"):
        raise AssertionError("jon2-config.js must define the public API endpoint setting.")
    parser = InlineScriptParser()
    parser.feed(html)
    parser.close()
    scripts = [(kind, source.strip()) for kind, source in parser.parts if source.strip()]
    if not scripts:
        raise ValueError(f"No inline JavaScript found in {html_path}.")

    combined = "\\n".join(source for _, source in scripts)
    required_contract = (
        "window.JON2_API_BASE_URL",
        '"/api/health"',
        '"/api/chat"',
        'api_version: "1"',
        "request_id: crypto.randomUUID()",
        "session_id: sessionId",
        "history: chatMessages.slice(0, -1)",
        "health.model_ready",
        "health.chat_ready === true",
        "payload.message",
        "apiNotReadyNote",
        "AbortSignal.timeout",
        "window.JON2_LOCAL_CLIENT.generate",
        "CHECKPOINT_SHA256",
        "weights.bin",
        "manifest.json",
    )
    missing = [marker for marker in required_contract if marker not in combined]
    if missing:
        raise AssertionError("Frontend chat/local-runtime contract is incomplete: " + ", ".join(missing))

    for index, (kind, source) in enumerate(scripts):
        suffix = ".mjs" if kind == "module" else ".js"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, encoding="utf-8", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(source)
        try:
            result = subprocess.run(
                ["node", "--check", str(temporary)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(f"Inline script {index + 1} syntax error: {result.stderr.strip()}")
        finally:
            temporary.unlink(missing_ok=True)
    print(f"JavaScript syntax: PASS ({html_path}, {len(scripts)} inline script block(s)).")
    return len(scripts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", nargs="?", default="index.html")
    args = parser.parse_args()
    check_inline_scripts(Path(args.html))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
