// Build the same bounded conversation prompt used by ai_engine/chat_engine.py.
export function buildJon2ConversationPrompt(message, history = [], tokenizer, context = 128) {
  if (typeof message !== "string" || !message.trim()) {
    throw new TypeError("اكتب رسالتك أولًا.");
  }
  if (!tokenizer || typeof tokenizer.encode !== "function") {
    throw new TypeError("Jon2 requires its native byte-BPE tokenizer.");
  }
  if (!Number.isInteger(context) || context < 2) {
    throw new TypeError("Jon2 context must be an integer greater than one.");
  }

  const question = message.trim();
  const turns = [];
  const recentHistory = Array.isArray(history) ? history.slice(-4) : [];
  for (const item of recentHistory) {
    const role = item?.role;
    const content = item?.content;
    if ((role !== "user" && role !== "assistant") ||
        typeof content !== "string" || !content.trim()) continue;
    const label = role === "user" ? "المستخدم" : "Jon2";
    const clipped = Array.from(content.trim()).slice(-90).join("");
    turns.push(label + ": " + clipped);
  }

  while (true) {
    const prompt = turns.concat(["المستخدم: " + question + "\nJon2:"]).join("\n");
    if (tokenizer.encode(prompt).length <= context - 1) return prompt;
    if (turns.length) {
      turns.shift();
      continue;
    }
    throw new RangeError(
      "سؤال المستخدم أطول من نافذة سياق نموذج Jon2؛ لن يتم اختصاره حتى لا يتغير معناه."
    );
  }
}
