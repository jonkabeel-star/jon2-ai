import random
import re
from collections import Counter, defaultdict

class Jon2LanguageEngine:
    def __init__(self):
        self.transitions = defaultdict(Counter)
        self.ready = False

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
            return "Jon2 AI needs training first."

        words = re.findall(r"\w+|[^\w\s]", prompt.lower())
        current = words[-1] if words else "<START>"
        result = words[:]

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

        return " ".join(result)

if __name__ == "__main__":
    engine = Jon2LanguageEngine()

    training_data = [
        "hello how are you",
        "hello I am Jon2 AI",
        "I am learning language",
        "Jon2 AI learns from text",
        "how are you today",
        "artificial intelligence learns patterns",
        "Jon2 AI is a language experiment",
    ]

    engine.train(training_data)

    print("Jon2 AI Language Engine")
    print(engine.generate("hello"))
