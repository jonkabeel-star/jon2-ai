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
        self.in_script = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.parts.append(data)


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
    source = "\n".join(parser.parts).strip()
    if not source:
        raise ValueError(f"No inline JavaScript found in {html_path}.")

    required_contract = (
        "window.JON2_API_BASE_URL",
        '"/api/health"',
        '"/api/chat"',
        "session_id: sessionId",
        "health.chat_ready",
        "apiNotReadyNote",
        "AbortSignal.timeout",
    )
    missing = [marker for marker in required_contract if marker not in source]
    if missing:
        raise AssertionError("Frontend chat API contract is incomplete: " + ", ".join(missing))

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", encoding="utf-8", delete=False
    ) as handle:
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
            raise RuntimeError(result.stderr.strip() or "Node.js syntax check failed.")
    finally:
        temporary.unlink(missing_ok=True)
    print(f"JavaScript syntax: PASS ({html_path}, {len(parser.parts)} inline script block(s)).")
    return len(parser.parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", nargs="?", default="index.html")
    args = parser.parse_args()
    check_inline_scripts(Path(args.html))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
