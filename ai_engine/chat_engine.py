import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = os.getenv(
    "JON2_CHAT_MODEL",
    "Qwen/Qwen2.5-0.5B-Instruct"
)
MAX_NEW_TOKENS = int(os.getenv("JON2_MAX_NEW_TOKENS", "160"))

tokenizer = None
model = None
device = "cuda" if torch.cuda.is_available() else "cpu"


def model_is_ready():
    return model is not None and tokenizer is not None


def load_model():
    global tokenizer, model
    if model_is_ready():
        return

    print(f"Loading Jon2 AI model: {MODEL_NAME} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True,
    )
    model.to(device)
    model.eval()
    print("Jon2 AI language model loaded successfully.")


def generate_reply(message):
    if not message or not message.strip():
        raise ValueError("Please enter a message.")

    if not model_is_ready():
        load_model()

    messages = [
        {
            "role": "system",
            "content": (
                "أنت Jon2 AI، مساعد ذكي مستقل. أجب بالعربية الفصحى "
                "الواضحة والطبيعية عندما يكتب المستخدم بالعربية. "
                "أجب مباشرة وبدقة، ولا تخترع معلومات أو أسماء أو أحداثًا. "
                "نظّم الإجابة في نقاط عند الحاجة."
            ),
        },
        {"role": "user", "content": message.strip()},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
    ).to(device)

    with torch.inference_mode():
        outputs = model.generate(
            inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            repetition_penalty=1.10,
            no_repeat_ngram_size=3,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = outputs[0][inputs.shape[-1]:]
    answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
    if not answer:
        raise RuntimeError("The model returned an empty response.")
    return answer
