// Conservative Arabic surface-integrity checks. These checks do not prove semantic correctness.
const ALLOWED_ANSWER = /^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»"'\-]+$/u;
const ARABIC_LETTERS = /[\u0621-\u064A\u066E-\u06D3]/gu;
const KNOWN_FRAGMENT_PATTERNS = [
  /الوصوليساعدة/u, /المولاك/u, /سخاطر/u, /استعلي/u,
  /افترك/u, /المتوى/u, /الجه\b/u, /الخطاء/u
];

export function inspectJon2ArabicAnswer(answer) {
  if (typeof answer !== "string") return { valid: false, reason: "not_text" };
  const text = answer.trim();
  const length = Array.from(text).length;
  if (length < 4 || length > 4000 || !ALLOWED_ANSWER.test(text)) return { valid: false, reason: "invalid_characters_or_length" };

  const visible = Array.from(text).filter(char => !/\s/u.test(char));
  const arabicCount = (text.match(ARABIC_LETTERS) || []).length;
  if (arabicCount / Math.max(1, visible.length) < 0.70) return { valid: false, reason: "low_arabic_ratio" };
  if (/(.)\1{3,}/u.test(text) || /(.{2,8})\1{2,}/u.test(text)) return { valid: false, reason: "character_repetition" };

  const words = text.split(/\s+/u).filter(Boolean);
  if (KNOWN_FRAGMENT_PATTERNS.some(pattern => pattern.test(text))) return { valid: false, reason: "known_fragment_pattern" };
  if (words.length >= 8) {
    for (const size of [1, 2, 3]) {
      for (let i = 0; i <= words.length - 3 * size; i++) {
        const a = words.slice(i, i + size).join("\u0000");
        const b = words.slice(i + size, i + 2 * size).join("\u0000");
        const c = words.slice(i + 2 * size, i + 3 * size).join("\u0000");
        if (a === b && b === c) return { valid: false, reason: "repeated_word_sequence" };
      }
    }
  }
  return { valid: true, reason: "surface_checks_passed" };
}

export function validateJon2ArabicAnswer(answer) {
  return inspectJon2ArabicAnswer(answer).valid;
}
