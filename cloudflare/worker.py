import json
from urllib.parse import urlsplit
from workers import WorkerEntrypoint, Response

ALLOWED_ORIGIN = "https://jonkabeel-star.github.io"

def json_response(payload, status=200, origin=ALLOWED_ORIGIN):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }
    return Response(json.dumps(payload, ensure_ascii=False), status=status, headers=headers)

class Default(WorkerEntrypoint):
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
