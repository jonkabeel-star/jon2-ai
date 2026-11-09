import json
from urllib.parse import urlsplit
from workers import WorkerEntrypoint, Response, fetch

ALLOWED_ORIGIN = "https://jonkabeel-star.github.io"
GITHUB_DISPATCH_URL = (
    "https://api.github.com/repos/jonkabeel-star/jon2-ai/"
    "actions/workflows/jon2-autonomous-builder.yml/dispatches"
)


def json_response(payload, status=200, origin=ALLOWED_ORIGIN):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }
    return Response(json.dumps(payload, ensure_ascii=False), status=status, headers=headers)


class Default(WorkerEntrypoint):
    async def scheduled(self, controller, env, ctx):
        """Dispatch one bounded, read-only brain assessment from the Cloudflare Cron Trigger."""
        token = getattr(env, "JON2_GITHUB_TOKEN", None)
        if not token:
            raise RuntimeError("Missing Cloudflare secret JON2_GITHUB_TOKEN")

        response = await fetch(
            GITHUB_DISPATCH_URL,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Jon2-Autonomous-Brain-Builder",
                "Content-Type": "application/json",
            },
            body=json.dumps({"ref": "main"}),
        )
        if response.status != 204:
            # Never log the token or GitHub response body; it may contain account details.
            raise RuntimeError(
                f"GitHub workflow dispatch failed with HTTP {response.status}"
            )
        print(f"Jon2 autonomous assessment dispatched; cron={controller.cron}")

    async def fetch(self, request):
        path = urlsplit(request.url).path.rstrip("/") or "/"
        method = request.method.upper()
        origin = request.headers.get("Origin", "")

        if origin and origin not in (ALLOWED_ORIGIN, "http://localhost:3000", "http://127.0.0.1:5500"):
            return json_response({"project": "Jon2 Cloud", "error": "origin_not_allowed"}, 403, "null")

        if method == "OPTIONS":
            return Response("", status=204, headers={
                "Access-Control-Allow-Origin": origin or ALLOWED_ORIGIN,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
                "Vary": "Origin",
            })

        if method == "GET" and path in ("/", "/api/health/live"):
            return json_response({
                "project": "Jon2 Cloud",
                "status": "alive",
                "service": "python-edge-api",
                "model_runtime": "not_connected",
            })

        if method == "GET" and path == "/api/health":
            return json_response({
                "project": "Jon2 Cloud",
                "status": "online",
                "api_ready": True,
                "model_ready": False,
                "model_status": "not_connected",
                "message": "واجهة Jon2 Cloud تعمل، لكن محرك النموذج الحقيقي لم يُربط بعد."
            })

        if method == "POST" and path == "/api/chat":
            return json_response({
                "project": "Jon2 Cloud",
                "error": "model_runtime_not_connected",
                "chat_ready": False,
                "message": "لم يتم ربط محرك Jon2 الحقيقي بعد. لن نولّد ردودًا وهمية."
            }, 503)

        return json_response({"project": "Jon2 Cloud", "error": "not_found"}, 404)
