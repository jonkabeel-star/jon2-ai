// Conservative browser-side parity port of ai_engine/answer_quality.py.
// This is a surface-integrity check, not a semantic or factuality guarantee.
const ALLOWED_ANSWER = /^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»"'\-]+$/u;
const ARABIC_LETTERS = /[\u0621-\u064A\u066E-\u06D3]/gu;

export function validateJon2ArabicAnswer(answer) {
  if (typeof answer !== "string") return false;
  const text = answer.trim();
  const length = Array.from(text).length;
  if (length < 4 || length > 4000 || !ALLOWED_ANSWER.test(text)) return false;

  const visible = Array.from(text).filter(char => !/\s/u.test(char));
  const arabicCount = (text.match(ARABIC_LETTERS) || []).length;
  if (arabicCount / Math.max(1, visible.length) < 0.70) return false;
  if (/(.)\1{3,}/u.test(text) || /(.{2,8})\1{2,}/u.test(text)) return false;

  const words = text.split(/\s+/u).filter(Boolean);
  if (words.length >= 8) {
    for (const size of [1, 2, 3]) {
      for (let i = 0; i <= words.length - 3 * size; i++) {
        const a = words.slice(i, i + size).join("\u0000");
        const b = words.slice(i + size, i + 2 * size).join("\u0000");
        const c = words.slice(i + 2 * size, i + 3 * size).join("\u0000");
        if (a === b && b === c) return false;
      }
    }
  }
  return true;
}
