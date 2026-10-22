import random
import re
from collections import Counter, defaultdict
class Jon2LanguageEngine:
    def __init__(self):
        self.transitions = defaultdict(Counter)
        self.ready = False
        self.training_data = [
            "Jon2 AI is an intelligent assistant.",
            "Jon2 AI helps people create new ideas.",
            "Artificial intelligence can understand language patterns.",
            "A good story has a beginning, middle, and ending.",
            "الذكاء الاصطناعي يساعد الإنسان على التعلم والإبداع.",
            "يمكن كتابة قصة ممتعة عن المغامرة والصداقة.",
            "يتعلم Jon2 AI الأنماط اللغوية من النصوص.",
            "التعاون والصداقة يساعدان على حل المشكلات.",
        ]
        self.train(self.training_data)
    def train(self, texts):
        self.transitions.clear()
        for text in texts:
            words = re.findall(r"\w+|[^\w\s]", text.lower())
            words = ["<START>"] + words + ["<END>"]
            for current_word, next_word in zip(
                words, words[1:]
            ):
                self.transitions[current_word][next_word] += 1
        self.ready = bool(self.transitions)
        return self.ready
    def generate(self, prompt="", max_words=40):
        if not self.ready:
            return "Jon2 AI language engine is not ready."
        prompt = prompt.strip()
        if not prompt:
            return "من فضلك اكتب سؤالك أولًا."
        words = re.findall(r"\w+|[^\w\s]", prompt.lower())
        current = words[-1] if words else "<START>"
        result = []
        for _ in range(max_words):
            choices = self.transitions.get(current)
            if not choices:
                current = "<START>"
                choices = self.transitions.get(current)
            if not choices:
                break
            next_word = random.choices(
                list(choices.keys()),
                weights=list(choices.values()),
                k=1
            )[0]
            if next_word == "<END>":
                break
            result.append(next_word)
            current = next_word
        if not result:
            return (
                "أنا Jon2 AI. المحرك اللغوي التجريبي يعمل، "
                "لكن قدراتي الحالية محدودة. "
                "أحتاج إلى نموذج لغوي أقوى لفهم الأسئلة والإجابة عنها."
            )
        return " ".join(result)
if __name__ == "__main__":
    engine = Jon2LanguageEngine()
    print("Jon2 AI Language Engine")
    print(engine.generate("hello"))
