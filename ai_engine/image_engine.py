import os
import io
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from diffusers import StableDiffusionPipeline
app = FastAPI(
    title="Jon2 AI Image Engine",
    description="AI Image Generation Engine",
    version="1.0.0"
)
MODEL_PATH = os.getenv(
    "JON2_MODEL_PATH",
    "./models/stable-diffusion-v1-5"
)
pipe = None
class ImageRequest(BaseModel):
    prompt: str
@app.get("/")
def home():
    return {
        "project": "Jon2 AI",
        "engine": "Image Generation",
        "status": "online"
    }
@app.on_event("startup")
def load_model():
    global pipe
    if not os.path.isdir(MODEL_PATH):
        print("AI model not found:", MODEL_PATH)
        return
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        pipe = StableDiffusionPipeline.from_pretrained(
            MODEL_PATH,
            torch_dtype=(
                torch.float16
                if device == "cuda"
                else torch.float32
            ),
            local_files_only=True,
            safety_checker=None
        )
        pipe = pipe.to(device)
        print("Jon2 AI image model loaded successfully.")
    except Exception as error:
        print("Model loading failed:", str(error))
@app.post("/generate")
def generate_image(request: ImageRequest):
    if pipe is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI model is not installed or "
                "could not be loaded."
            )
        )
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter an image description."
        )
    try:
        result = pipe(
            prompt=request.prompt,
            num_inference_steps=25,
            width=512,
            height=512
        )
        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return Response(
            content=buffer.getvalue(),
            media_type="image/png"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Image generation failed."
        )
