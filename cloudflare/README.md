# Jon2 AI Qwen3.5 runtime

## What this adds

- A private FastAPI runtime for the official instruction-tuned `Qwen/Qwen3.5-4B` model.
- Optional Jon2 LoRA loading when a trained adapter is supplied.
- A bearer-token-protected `GET /v1/health` and `POST /v1/chat` contract.
- A Cloudflare edge gateway that proxies to the private runtime without exposing its token to the browser.
- Independent fail-closed public-release gates. The gateway will not serve public chat until the runtime reports model loaded, inference tested, human quality review passed, and public chat enabled; Cloudflare must also have `JON2_PUBLIC_CHAT_ENABLED=true`.

## Important model distinction

Until a Jon2 adapter has been trained and evaluated, replies come from the third-party Qwen3.5-4B instruction model. They must be described as a Qwen-powered Jon2 preview, not as a fully Jon2-trained model. The Qwen model card declares Apache-2.0; retain its license and notices. The Jon2 adapter does not exist yet.

## Runtime environment

Install the CUDA-enabled PyTorch build appropriate to the GPU first, then install `ai_engine/requirements-qwen35-runtime.txt`.

Set these environment variables on the private GPU host (never commit values):

- `JON2_BASE_MODEL=Qwen/Qwen3.5-4B`
- `JON2_RUNTIME_TOKEN`: random secret with at least 32 characters
- `JON2_ADAPTER_PATH`: optional directory containing a compatible `adapter_config.json`
- `JON2_INFERENCE_TESTED=false`
- `JON2_QUALITY_REVIEW_PASSED=false`
- `JON2_PUBLIC_CHAT_ENABLED=false`

Start the API with:

```bash
uvicorn ai_engine.jon2_qwen35_server:app --host 0.0.0.0 --port 8000
```

The runtime requires CUDA and loads the 4-bit model on GPU 0. A T4 may still fail from VRAM or kernel incompatibility; the health route reports the failure and the service must not be treated as ready until a real inference test succeeds.

## Cloudflare Worker bindings

Deploy the root `wrangler.toml` entry point (`cloudflare/worker.js`) only after a reachable private HTTPS runtime exists. Configure:

- Secret `JON2_RUNTIME_TOKEN`: same secret as the Python runtime.
- Variable `JON2_RUNTIME_URL`: HTTPS origin only, no path (for example `https://runtime.example.com`).
- Variable `JON2_PUBLIC_CHAT_ENABLED=false` until human review and explicit owner release approval.

Then set `window.JON2_API_BASE_URL` in `jon2-config.js` to the deployed Worker origin. The static GitHub Pages site cannot itself host Python or GPU inference; the Worker is a secure proxy only.

## Current project blockers

- The current private dataset contains 32 train and 12 evaluation records; all are pending human and rights review. This does not meet the trainer's 100/30 minimums.
- No Jon2 LoRA adapter has been produced.
- Kaggle free GPU sessions are temporary and are not a persistent production host.
- No Worker, GPU host, secrets, or website deployment is configured by this source change.
