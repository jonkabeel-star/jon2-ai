import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = os.getenv(
    "JON2_CHAT_MODEL",
    "Qwen/Qwen2.5-0.5B-Instruct"
)

tokenizer = None
model = None
device = "cuda" if torch.cuda.is_available() else "cpu"


def load_model():
    global tokenizer, model

    if model is not None:
        return

    print("Loading Jon2 AI Chat Model...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32
    )

    model.to(device)
    model.eval()

    print("Jon2 AI Chat Model is ready!")


def generate_reply(message):
    if not message or not message.strip():
        raise ValueError("Please enter a message.")

    load_model()

    messages = [
        {
            "role": "system",
            "content": (
                "You are Jon2 AI, an intelligent assistant. "
                "Reply clearly and naturally in the same language "
                "used by the user. For Arabic, use natural Arabic."
            )
        },
        {
            "role": "user",
            "content": message.strip()
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(device)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]

    return tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    ).strip()
