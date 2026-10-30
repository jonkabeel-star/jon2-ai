# Jon2 AI — Python Chat API

This folder contains the independent Jon2 AI chat backend.

## Deploy on Render

Create a **Web Service** connected to this repository and configure:

- Root Directory: `ai_engine`
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`

Optional environment variables:

- `JON2_CHAT_MODEL=Qwen/Qwen2.5-0.5B-Instruct`
- `JON2_MAX_NEW_TOKENS=160`

The model loads on the first chat request, not during the deploy startup. The first request can take several minutes while model weights are downloaded. The service needs enough RAM for PyTorch and the model; a small/free instance may run out of memory.

## Test after deployment

Open:

- `https://YOUR-SERVICE.onrender.com/api/health`
- `https://YOUR-SERVICE.onrender.com/docs`

Then send a POST request to `/api/chat` with JSON:

```json
{"message":"اكتب تعريفًا قصيرًا بنفسك"}
```

A successful response contains a `reply` field. A healthy API response alone does not prove that the model has loaded; check `model_loaded` and test a chat request.

## Frontend

The GitHub Pages frontend must send requests to the deployed Render service URL, not to its own `/api/chat` path. Set that URL in the frontend after the Render service has been created.
