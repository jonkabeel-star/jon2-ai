import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
class Jon2LanguageEngine:
    def __init__(self):
        self.model_name = os.getenv(
            "JON2_MODEL_NAME",
            "Qwen/Qwen2.5-0.5B-Instruct"
        )
        self.tokenizer = None
        self.model = None
        self.ready = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    def load_model(self):
        """Load the open-source language model."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=(
                    torch.float16
                    if self.device == "cuda"
                    else torch.float32
                )
            )
            self.model.to(self.device)
            self.model.eval()
            self.ready = True
            return True
        except Exception as error:
            self.ready = False
            print(f"Jon2 model loading failed: {error}")
            return False
    def generate(self, prompt="", max_words=300):
        """Generate a response using the real language model."""
        prompt = str(prompt).strip()
        if not prompt:
            return "من فضلك اكتب سؤالك أولًا."
        if not self.ready:
            if not self.load_model():
                return (
                    "محرك Jon2 AI غير جاهز حاليًا. "
                    "تأكد من تثبيت المتطلبات وتوفر اتصال "
                    "بالإنترنت وذاكرة كافية."
                )
        messages = [
            {
                "role": "system",
                "content": (
                    "أنت Jon2 AI، مساعد ذكي يتحدث العربية "
                    "الفصحى الواضحة والطبيعية. أجب عن السؤال "
                    "مباشرة، وكن دقيقًا ومفيدًا. استخدم لغة "
                    "السؤال عندما تكون مناسبة. لا تخترع معلومات."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
        try:
            input_ids = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.inference_mode():
                output_ids = self.model.generate(
                    input_ids,
                    max_new_tokens=max(64, min(max_words, 500)),
                    do_sample=False,
                    repetition_penalty=1.08,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            new_tokens = output_ids[0][input_ids.shape[-1]:]
            answer = self.tokenizer.decode(
                new_tokens,
                skip_special_tokens=True,
            ).strip()
            return answer or "لم أتمكن من إنشاء إجابة. حاول مرة أخرى."
        except Exception as error:
            print(f"Jon2 generation failed: {error}")
            return "حدث خطأ أثناء توليد الإجابة. حاول مرة أخرى."
if __name__ == "__main__":
    engine = Jon2LanguageEngine()
    if engine.load_model():
        print("Jon2 AI is ready!")
        print(engine.generate("اكتب قصة قصيرة عن الصداقة."))
    else:
        print("تعذر تحميل النموذج.")
